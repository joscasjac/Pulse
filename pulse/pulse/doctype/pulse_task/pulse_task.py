import frappe
from frappe.model.document import Document

class PulseTask(Document):
    def validate(self):
        if not self.pulse_rank:
            max_rank = frappe.db.sql(
                """SELECT MAX(pulse_rank) FROM `tabPulse Task` WHERE project=%s""",
                self.project,
            )
            self.pulse_rank = (max_rank[0][0] or 0) + 1 if max_rank else 1
