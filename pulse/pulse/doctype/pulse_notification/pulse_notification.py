import frappe
from frappe.model.document import Document


class PulseNotification(Document):
    def validate(self):
        # Delivery is server-owned. Inbox updates use the narrow recipient API.
        if not self.flags.ignore_permissions:
            frappe.throw("Notifications are created by Pulse. Use the notification inbox to mark them read.", frappe.PermissionError)
