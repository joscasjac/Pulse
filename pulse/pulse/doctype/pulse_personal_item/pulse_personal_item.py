import frappe
from frappe.model.document import Document


class PulsePersonalItem(Document):
    def validate(self):
        # The narrow API computes both the owner and deterministic record ID.
        if not self.flags.ignore_permissions:
            frappe.throw("Use Pulse favorite and follow controls to update personal items.", frappe.PermissionError)
