"""Permission-scoped request intake, with atomic conversion to native Task."""
import frappe
from pulse.hooks.permissions import require_permission, scoped_query_conditions, scoped_has_permission
from pulse.pulse.doctype.pulse_request.pulse_request import can_review


def query_conditions(user=None):
    return scoped_query_conditions(user, "Pulse Request")


def has_permission(doc, user=None, ptype=None, permission_type=None):
    # Frappe 16 treats a falsey hook result as a veto, including None.
    # Native role permissions remain responsible for granting the operation.
    return scoped_has_permission(doc, user, ptype=ptype, permission_type=permission_type) is not False


@frappe.whitelist()
def list_requests(project=None, status=None):
    filters = {}
    if project:
        require_permission("Project", project)
        filters["project"] = project
    if status:
        filters["status"] = status
    return frappe.get_list("Pulse Request", filters=filters,
                           fields=["name", "title", "project", "status", "reviewer", "accepted_task", "modified"],
                           order_by="modified desc", limit_page_length=0)


@frappe.whitelist()
def reviewer_options(project):
    doc = require_permission("Project", project)
    users = {r.user for r in doc.get("users") or []} | {doc.owner, frappe.session.user}
    return [{"name": user, "full_name": frappe.db.get_value("User", user, "full_name") or user}
            for user in sorted(users) if user != "Guest" and frappe.db.get_value("User", user, "enabled")
            and frappe.has_permission("Project", "read", doc=doc, user=user)]


@frappe.whitelist()
def create_request(project, title, description="", reviewer=None):
    require_permission("Project", project)
    doc = frappe.get_doc({"doctype": "Pulse Request", "project": project, "title": title,
                           "description": description, "reviewer": reviewer, "status": "Incoming"})
    doc.insert()
    return get_request(doc.name)


@frappe.whitelist()
def get_request(name):
    doc = require_permission("Pulse Request", name)
    result = doc.as_dict()
    result["can_review"] = can_review(doc) and frappe.has_permission("Pulse Request", "write", doc=doc)
    return result


def _reviewable(name, allow_accepted=False):
    require_permission("Pulse Request", name, "write")
    frappe.db.sql("SELECT name FROM `tabPulse Request` WHERE name=%s FOR UPDATE", (name,))
    doc = require_permission("Pulse Request", name, "write")
    if allow_accepted and doc.status == "Accepted" and doc.accepted_task:
        return doc
    if not can_review(doc):
        frappe.throw("Only the assigned reviewer or a project lead may review this request.", frappe.PermissionError)
    return doc


@frappe.whitelist()
def review_request(name, status, reviewer=None, duplicate_of=None, note=None):
    if status not in {"Incoming", "Deferred", "Rejected", "Duplicate"}:
        frappe.throw("Choose Incoming, Deferred, Rejected or Duplicate.")
    doc = _reviewable(name)
    if doc.status == "Accepted":
        frappe.throw("Accepted requests cannot be reviewed again.")
    doc.status = status
    if reviewer is not None:
        doc.reviewer = reviewer or None
    doc.duplicate_of = duplicate_of
    doc.review_note = note
    doc.save()
    return get_request(name)


@frappe.whitelist()
def accept_request(name, reviewer=None, note=None):
    doc = _reviewable(name, allow_accepted=True)
    if doc.accepted_task:
        require_permission("Task", doc.accepted_task)
        return {"task": doc.accepted_task}
    if doc.status not in {"Incoming", "Deferred"}:
        frappe.throw("Only incoming or deferred requests may be accepted.")
    from pulse.api.task_config import get_config, CATEGORY_STATUS
    config = get_config(doc.project)
    initial = next((s for s in config["statuses"] if s["category"] not in {"Done", "Cancelled"}), config["statuses"][0])
    task = frappe.get_doc({"doctype": "Task", "subject": doc.title, "description": doc.description,
                           "project": doc.project, "workflow_state": initial["label"], "status": CATEGORY_STATUS[initial["category"]]})
    # Do not call create_task: its explicit commit would break atomic conversion.
    task.insert()
    previous = frappe.flags.get("pulse_accepting_request")
    try:
        frappe.flags.pulse_accepting_request = True
        doc.status = "Accepted"
        doc.accepted_task = task.name
        if reviewer is not None:
            doc.reviewer = reviewer or None
        doc.review_note = "Accepted as " + (task.get("issue_key") or task.name)
        if note:
            doc.review_note += " — " + str(note)
        doc.save()
    finally:
        frappe.flags.pulse_accepting_request = previous
    return {"task": task.name}
