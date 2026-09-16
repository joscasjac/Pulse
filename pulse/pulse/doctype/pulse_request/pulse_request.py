import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from pulse.hooks.permissions import require_permission


def can_review(doc, user=None):
    user = user or frappe.session.user
    return (user == "Administrator" or user == doc.reviewer
            or bool(set(frappe.get_roles(user)) & {"System Manager", "Pulse Admin", "Pulse Manager", "Pulse Team Lead"}))


class PulseRequest(Document):
    def validate(self):
        public_submission = self.is_new() and frappe.flags.get("pulse_public_request_project") == self.project
        if not public_submission:
            require_permission("Project", self.project)
        self.title = (self.title or "").strip()
        if len(self.title) > 140 or len(self.description or "") > 20000:
            frappe.throw("Use a title of at most 140 characters and a description of at most 20,000 characters.")
        if not self.title:
            frappe.throw("A request needs a title.")
        if self.status != "Duplicate":
            self.duplicate_of = None
        old = self.get_doc_before_save()
        if self.reviewer:
            if not frappe.db.get_value("User", self.reviewer, "enabled"):
                frappe.throw("Choose an enabled reviewer.")
            if not frappe.has_permission("Project", "read", doc=frappe.get_doc("Project", self.project), user=self.reviewer):
                frappe.throw("The reviewer must have access to the project.")
        if old:
            if self.project != old.project:
                frappe.throw("Requests cannot be moved between projects.")
            if [(r.action, r.status, r.note, r.by, str(r.at), r.reviewer, r.duplicate_of) for r in self.activity] != [(r.action, r.status, r.note, r.by, str(r.at), r.reviewer, r.duplicate_of) for r in old.activity]:
                frappe.throw("Request history cannot be edited.")
            if old.status == "Accepted" and self.as_dict() != old.as_dict():
                # Ignore housekeeping changes, but keep the accepted source immutable.
                for field in ("title", "description", "status", "reviewer", "duplicate_of", "accepted_task", "review_note"):
                    if self.get(field) != old.get(field):
                        frappe.throw("Accepted requests are preserved. Edit the linked task instead.")
            changed = any(self.get(f) != old.get(f) for f in ("status", "reviewer", "duplicate_of", "review_note", "accepted_task"))
            if changed and not can_review(old):
                frappe.throw("Only the assigned reviewer or a project lead may review this request.", frappe.PermissionError)
            if self.accepted_task != old.accepted_task or (self.status == "Accepted" and old.status != "Accepted"):
                if not frappe.flags.get("pulse_accepting_request"):
                    frappe.throw("Use Accept to create a linked task and preserve request history.")
            if changed:
                self.append("activity", {"action": "Accepted" if self.status == "Accepted" else "Reviewed", "status": self.status,
                                         "reviewer": self.reviewer, "duplicate_of": self.duplicate_of,
                                         "note": self.review_note, "by": frappe.session.user, "at": now_datetime()})
        else:
            if self.status != "Incoming" or self.accepted_task or self.duplicate_of:
                frappe.throw("New requests must start in Incoming.")
            self.set("activity", [])
            self.append("activity", {"action": "Created", "status": "Incoming", "reviewer": self.reviewer, "by": frappe.session.user, "at": now_datetime()})
        if self.status == "Duplicate":
            if not self.duplicate_of or self.duplicate_of == self.name:
                frappe.throw("Choose a different request as the duplicate target.")
            visited = {self.name}
            target = self.duplicate_of
            while target:
                if target in visited:
                    frappe.throw("Duplicate requests cannot form a cycle.")
                visited.add(target)
                # Lock each edge so concurrent reciprocal duplicate decisions cannot
                # both validate against the old chain. A deadlock rolls one back.
                rows = frappe.db.sql("SELECT name, project, status, duplicate_of FROM `tabPulse Request` WHERE name=%s FOR UPDATE", (target,), as_dict=True)
                require_permission("Pulse Request", target)
                if not rows:
                    frappe.throw("The duplicate target no longer exists.")
                other = rows[0]
                if other.project != self.project:
                    frappe.throw("The duplicate target must belong to the same project.")
                target = other.duplicate_of if other.status == "Duplicate" else None
        else:
            self.duplicate_of = None
