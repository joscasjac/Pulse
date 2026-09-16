import secrets
import frappe
from frappe.model.document import Document
from pulse.hooks.permissions import require_permission


def require_form_admin(project):
    if frappe.session.user != "Administrator" and not set(frappe.get_roles()) & {"System Manager", "Pulse Admin"}:
        frappe.throw("Only an administrator can manage public request forms.", frappe.PermissionError)
    return require_permission("Project", project, "write")


class PulseRequestForm(Document):
    def validate(self):
        require_form_admin(self.project)
        old = self.get_doc_before_save()
        if old and self.project != old.project:
            frappe.throw("A public form cannot be moved between projects.")
        self.public_title = (self.public_title or "").strip()
        if not self.public_title or len(self.public_title) > 140 or len(self.public_description or "") > 2000:
            frappe.throw("Provide a public title up to 140 characters and instructions up to 2,000 characters.")
        # Generate on the server; enabling again revokes all previously shared links.
        if not old or (self.enabled and not old.enabled):
            self.access_key = secrets.token_urlsafe(32)
        else:
            self.access_key = old.access_key
