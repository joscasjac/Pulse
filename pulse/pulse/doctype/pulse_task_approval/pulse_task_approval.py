import frappe
from frappe.model.document import Document


class PulseTaskApproval(Document):
    def validate(self):
        if not frappe.flags.get('pulse_approval_action'):
            frappe.throw('Use the task approval actions to preserve the approval record.', frappe.PermissionError)

    def on_trash(self):
        if not frappe.flags.in_test and frappe.session.user != 'Administrator':
            frappe.throw('Approval history cannot be deleted.', frappe.PermissionError)
