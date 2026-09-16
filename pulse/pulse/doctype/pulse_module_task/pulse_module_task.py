import frappe
from frappe.model.document import Document
from pulse.hooks.permissions import require_permission

class PulseModuleTask(Document):
    def validate(self):
        frappe.db.sql("SELECT name FROM `tabPulse Module` WHERE name=%s FOR UPDATE", (self.module,))
        current_project = frappe.db.get_value("Task", self.task, "project", for_update=True)
        module = require_permission("Pulse Module", self.module, "write")
        task = require_permission("Task", self.task, "write")
        if task.project != module.project or current_project != module.project:
            frappe.throw("Tasks and module must belong to the same project.")
        self.project = module.project
        old = self.get_doc_before_save()
        if old and (old.module != self.module or old.task != self.task):
            frappe.throw("Remove the membership and add a new one instead.")
        existing = frappe.db.get_value("Pulse Module Task", {"module": self.module, "task": self.task}, "name", for_update=True)
        if existing and existing != self.name:
            frappe.throw("Task is already in this module.")

    def on_trash(self):
        require_permission("Pulse Module", self.module, "write")
        require_permission("Task", self.task, "write")
