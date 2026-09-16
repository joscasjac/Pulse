import frappe
from frappe.model.document import Document
from pulse.hooks.permissions import require_permission

class PulseModule(Document):
    def validate(self):
        require_permission("Project", self.project)
        old = self.get_doc_before_save()
        if old and old.project != self.project:
            frappe.throw("A module cannot move between projects.")
        self.title = (self.title or "").strip()
        if not self.title:
            frappe.throw("A module title is required.")
        if self.start_date and self.due_date and str(self.start_date) > str(self.due_date):
            frappe.throw("Due date must be on or after start date.")
        if self.lead and not frappe.has_permission("Project", "read", doc=self.project, user=self.lead):
            frappe.throw("Module lead must have access to this project.")
