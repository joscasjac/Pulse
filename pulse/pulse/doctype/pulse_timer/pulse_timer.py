import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from pulse.hooks.permissions import require_permission


class PulseTimer(Document):
    def before_insert(self):
        # REST clients cannot forge elapsed time; native manual entries handle corrections.
        self.started_at = now_datetime()

    def validate(self):
        if self.user != frappe.session.user or self.owner != frappe.session.user:
            frappe.throw("You can only operate your own timer.", frappe.PermissionError)
        before = self.get_doc_before_save()
        if before and any(self.get(field) != before.get(field)
                          for field in ("user", "task", "started_at", "billable")):
            frappe.throw("A running timer cannot be changed. Stop or discard it first.")
        require_permission("Task", self.task)

    def on_trash(self):
        if self.user != frappe.session.user:
            frappe.throw("You can only discard your own timer.", frappe.PermissionError)
