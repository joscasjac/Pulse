import frappe
from frappe import _
from frappe.model.document import Document

MANAGER_ROLES = {"Pulse Admin", "Pulse Manager", "System Manager"}


class PulseDashboard(Document):
    def validate(self):
        # Default a personal dashboard to the current user.
        if self.scope == "Personal" and not self.owner_user:
            self.owner_user = frappe.session.user

        roles = set(frappe.get_roles(frappe.session.user))
        is_manager = bool(roles & MANAGER_ROLES)

        # Non-managers may only own personal dashboards, and only their own.
        if not is_manager:
            if self.scope != "Personal":
                frappe.throw(
                    _("Only Pulse Admins or Managers can create shared dashboards."),
                    title=_("Not allowed"),
                )
            if self.owner_user != frappe.session.user:
                frappe.throw(
                    _("You can only manage your own dashboard."),
                    title=_("Not allowed"),
                )
            # Regular users can't publish templates.
            self.is_default = 0
