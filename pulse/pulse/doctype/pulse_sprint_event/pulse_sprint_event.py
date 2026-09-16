import frappe
from frappe.model.document import Document


class PulseSprintEvent(Document):
    def before_save(self):
        if not self.is_new():
            frappe.throw("Sprint history is immutable.")

    def on_trash(self):
        if not frappe.flags.in_uninstall:
            frappe.throw("Sprint history is immutable.")
