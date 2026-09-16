import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt


class PulseAllocation(Document):
    def validate(self):
        if getdate(self.end_date) < getdate(self.start_date):
            frappe.throw('Allocation end date must be on or after its start date.')
        if not 0 <= flt(self.allocation_percentage) <= 100:
            frappe.throw('Allocation percentage must be between 0 and 100.')
