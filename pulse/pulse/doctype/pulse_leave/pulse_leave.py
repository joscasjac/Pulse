import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class PulseLeave(Document):
    def validate(self):
        if getdate(self.end_date) < getdate(self.start_date):
            frappe.throw('Leave end date must be on or after its start date.')
