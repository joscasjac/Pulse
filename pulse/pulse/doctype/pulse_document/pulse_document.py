import frappe
from frappe.model.document import Document
from frappe.utils import sanitize_html
from pulse.hooks.permissions import require_permission

class PulseDocument(Document):
    def validate(self):
        if not self.project:
            frappe.throw("Select a project for this page")
        require_permission("Project", self.project)
        if not (self.title or "").strip():
            frappe.throw("A page title is required")
        self.content = safe_mentions(sanitize_html(self.content or ""), self)
        before = self.get_doc_before_save()
        if before and before.project != self.project:
            frappe.throw("A page cannot be moved to another project")
        if self.parent_doc:
            parent = require_permission("Pulse Document", self.parent_doc)
            if parent.project != self.project or parent.name == self.name:
                frappe.throw("Parent page must be another page in this project")
        for row in self.get("task_links") or []:
            task = require_permission("Task", row.task)
            if task.project != self.project:
                frappe.throw("Linked tasks must belong to this project")

    def on_update(self):
        from frappe.desk.notifications import extract_mentions, notify_mentions
        before = self.get_doc_before_save()
        old = set(extract_mentions(before.content or "")) if before else set()
        if set(extract_mentions(self.content or "")) - old:
            notify_mentions(self.doctype, self.name, self.content)

    def notify_update(self):
        # A document-room subscription outlives project membership. Override
        # Frappe's default doc_update/list_update broadcasts as well as our own
        # event, and check recipients after this transaction has committed.
        if any(frappe.flags.get(flag) for flag in ("in_import", "in_patch", "in_migrate", "in_install")):
            return
        from functools import partial
        frappe.db.after_commit.add(partial(publish_page_update, self.name))


def safe_mentions(content, doc):
    """Keep mention notifications within the page's visibility boundary."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content or "", "html.parser")
    for mention in soup.find_all(class_="mention"):
        user = mention.get("data-id")
        if not user or mention.get("data-is-group") == "true" or not frappe.has_permission("Project", "read", doc=doc.project, user=user):
            mention.unwrap()
    return str(soup)


def publish_page_update(name):
    """Publish only to readers who are authorized at delivery time.

    Never address retained document/list rooms: their membership can be stale.
    Personal rooms are bound to each authenticated socket by Frappe.
    """
    if not frappe.db.exists("Pulse Document", name):
        return
    doc = frappe.get_doc("Pulse Document", name)
    for user in frappe.get_all("User", filters={"enabled": 1, "name": ["!=", "Guest"]}, pluck="name"):
        if not frappe.has_permission("Pulse Document", "read", doc=doc, user=user):
            continue
        frappe.publish_realtime("pulse_page_updated", {
            "name": doc.name, "modified": str(doc.modified), "by": doc.modified_by,
        }, user=user)
        frappe.publish_realtime("doc_update", {
            "doctype": doc.doctype, "name": doc.name, "modified": str(doc.modified),
        }, user=user)
        frappe.publish_realtime("list_update", {
            "doctype": doc.doctype, "name": doc.name, "user": doc.modified_by,
        }, user=user)
