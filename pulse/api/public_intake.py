"""Public capability links expose only explicitly authored form copy."""
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, escape_html, get_url
from pulse.pulse.doctype.pulse_request_form.pulse_request_form import require_form_admin


def _settings(doc):
    return {"enabled": bool(doc.enabled), "public_title": doc.public_title,
            "public_description": doc.public_description or "",
            "url": get_url("/pulse-request?key=" + doc.access_key) if doc.enabled else None}


@frappe.whitelist()
def get_settings(project):
    require_form_admin(project)
    name = frappe.db.get_value("Pulse Request Form", {"project": project}, "name")
    return _settings(frappe.get_doc("Pulse Request Form", name)) if name else {"enabled": False, "public_title": "Submit a request", "public_description": "", "url": None}


@frappe.whitelist(methods=["POST"])
def save_settings(project, enabled, public_title="Submit a request", public_description=""):
    require_form_admin(project)
    # Serializes first creation and key rotation for this project.
    frappe.db.sql("SELECT name FROM `tabProject` WHERE name=%s FOR UPDATE", (project,))
    name = frappe.db.get_value("Pulse Request Form", {"project": project}, "name")
    doc = frappe.get_doc("Pulse Request Form", name) if name else frappe.new_doc("Pulse Request Form")
    doc.update({"project": project, "enabled": cint(enabled), "public_title": public_title,
                "public_description": public_description})
    doc.save()
    return _settings(doc)


def _public_form(key, lock=False):
    if not isinstance(key, str) or not 40 <= len(key) <= 100:
        frappe.throw("This request form is unavailable.", frappe.DoesNotExistError)
    rows = frappe.db.sql("SELECT name FROM `tabPulse Request Form` WHERE access_key=%s AND enabled=1" + (" FOR UPDATE" if lock else ""), (key,))
    if not rows:
        frappe.throw("This request form is unavailable.", frappe.DoesNotExistError)
    return frappe.get_doc("Pulse Request Form", rows[0][0])


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60)
def get_form(key):
    doc = _public_form(key)
    return {"title": doc.public_title, "description": doc.public_description or ""}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60)
def submit(key, title, description=""):
    form = _public_form(key, lock=True)
    if not isinstance(title, str) or not isinstance(description, str):
        frappe.throw("Enter a title and description as text.")
    previous = frappe.flags.get("pulse_public_request_project")
    try:
        frappe.flags.pulse_public_request_project = form.project
        doc = frappe.get_doc({"doctype": "Pulse Request", "project": form.project,
                              "title": title, "description": escape_html(description), "status": "Incoming"})
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.pulse_public_request_project = previous
    # Never return project, request ID, reviewers, or any private record fields.
    return {"submitted": True}


@frappe.whitelist()
def can_manage():
    return frappe.session.user == "Administrator" or bool(set(frappe.get_roles()) & {"System Manager", "Pulse Admin"})
