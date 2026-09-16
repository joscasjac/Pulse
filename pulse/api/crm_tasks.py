"""Optional Frappe CRM task access. CRM Task remains the only writable record."""
from urllib.parse import quote

import frappe

FIELDS = ["name", "title", "status", "priority", "assigned_to", "start_date", "due_date", "reference_doctype", "reference_docname", "modified"]
EDITABLE = {"title", "status", "priority", "start_date", "due_date"}
REFERENCES = {"CRM Lead": "leads", "CRM Deal": "deals"}


def available():
    return "crm" in frappe.get_installed_apps() and bool(frappe.db.exists("DocType", "CRM Task"))


def _reference_allowed(doc):
    kind, name = doc.get("reference_doctype"), doc.get("reference_docname")
    if not kind and not name:
        return True
    return bool(kind in REFERENCES and name and frappe.has_permission(kind, "read", doc=name))


def _row(doc):
    row = {key: doc.get(key) for key in FIELDS}
    row["source"] = "frappe_crm"
    row["identity"] = "frappe_crm:CRM Task:" + str(doc.name)
    row["can_write"] = bool(frappe.has_permission("CRM Task", "write", doc=doc))
    kind, name = doc.get("reference_doctype"), doc.get("reference_docname")
    row["reference_url"] = f"/crm/{REFERENCES[kind]}/{quote(str(name), safe='')}" if kind in REFERENCES and name else None
    return row


@frappe.whitelist()
def mine():
    if not available():
        return {"available": False, "tasks": []}
    if not frappe.has_permission("CRM Task", "read"):
        return {"available": True, "tasks": []}
    # Framework list permissions plus document and parent checks prevent a task
    # share from inadvertently exposing a restricted deal's follow-up text.
    rows = frappe.get_list("CRM Task", filters={"assigned_to": frappe.session.user},
                           fields=FIELDS, order_by="due_date asc, modified desc", limit_page_length=0)
    tasks = []
    for row in rows:
        if not _reference_allowed(row):
            continue
        doc = frappe.get_doc("CRM Task", row.name)
        if _reference_allowed(doc) and doc.assigned_to == frappe.session.user and frappe.has_permission("CRM Task", "read", doc=doc):
            tasks.append(_row(doc))
    return {"available": True, "tasks": tasks}


@frappe.whitelist(methods=["POST"])
def update(task, fields, modified):
    if not available():
        frappe.throw("Frappe CRM is not installed on this site.")
    fields = frappe.parse_json(fields) if isinstance(fields, str) else fields
    if not isinstance(fields, dict) or not fields or set(fields) - EDITABLE:
        frappe.throw("Choose supported CRM task fields.")
    doc = frappe.get_doc("CRM Task", task)
    doc.check_permission("read")
    doc.check_permission("write")
    if not _reference_allowed(doc):
        frappe.throw("You do not have access to this CRM record.", frappe.PermissionError)
    if str(doc.modified) != str(modified):
        frappe.throw("This CRM task changed. Refresh before saving.", frappe.TimestampMismatchError)
    for key in ("status", "priority"):
        if key in fields:
            allowed = (doc.meta.get_field(key).options or "").splitlines()
            if fields[key] not in allowed:
                frappe.throw("Choose a valid CRM task " + key + ".")
    if "title" in fields and (not isinstance(fields["title"], str) or not fields["title"].strip()):
        frappe.throw("A task title is required.")
    doc.update(fields)
    if doc.start_date and doc.due_date and frappe.utils.getdate(doc.start_date) > frappe.utils.getdate(doc.due_date):
        frappe.throw("Due date must be on or after start date.")
    doc.save()
    return _row(doc)
