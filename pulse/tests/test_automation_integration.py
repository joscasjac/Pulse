import frappe
from frappe.tests import IntegrationTestCase
from pulse.api.automation import execute


class TestAutomationIntegration(IntegrationTestCase):
    def test_project_task_and_module_flow_uses_native_records(self):
        frappe.set_user("Administrator")
        project = execute("create_project", {"project_name": "Automation acceptance " + frappe.generate_hash(length=8)})
        tasks = []
        module = None
        try:
            module = execute("create_module", {"project": project["name"], "title": "Delivery"})
            task = execute("create_task", {"project": project["name"], "subject": "Automated delivery",
                "module": module["name"], "exp_start_date": "2026-09-16", "exp_end_date": "2026-09-18"})
            tasks.append(task["name"])
            self.assertTrue(frappe.db.exists("Task", task["name"]))
            execute("update_task", {"task": task["name"], "fields": {"expected_time": 3, "exp_end_date": "2026-09-20"}})
            execute("assign_task", {"task": task["name"], "user": "Administrator"})
            self.assertTrue(frappe.db.exists("ToDo", {"reference_type": "Task", "reference_name": task["name"], "allocated_to": "Administrator"}))
            execute("add_comment", {"task": task["name"], "text": "Created from automation"})
            execute("set_status", {"task": task["name"], "state": "Done"})
            native = frappe.get_doc("Task", task["name"])
            self.assertEqual(native.status, "Completed")
            self.assertEqual(native.expected_time, 3)
            self.assertEqual(str(native.exp_end_date)[:10], "2026-09-20")
            from pulse.api.modules import get_module
            self.assertEqual(get_module(module["name"])["percentage"], 100)
            execute("get_task", {"task": task["name"]})
        finally:
            from pulse.api.spa import delete_task
            for name in tasks:
                delete_task(name)
            if module:
                frappe.delete_doc("Pulse Module", module["name"], force=True)
            frappe.delete_doc("Project", project["name"], force=True)
            frappe.db.commit()
