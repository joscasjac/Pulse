import frappe
from unittest.mock import patch
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


class TestExpandedAutomation(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.commit_patch = patch.object(frappe.db, "commit")
        self.commit_patch.start()
        self.project = execute("create_project", {"project_name": "Action coverage " + frappe.generate_hash(length=8)})
        self.task = execute("create_task", {"project": self.project["name"], "subject": "Automation parent"})

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        self.commit_patch.stop()

    def test_tasks_modules_checklists_and_archive_roundtrip(self):
        project, task = self.project["name"], self.task["name"]
        execute("update_project", {"project": project, "fields": {"project_name": "Updated automation project"}})
        self.assertEqual(execute("get_project", {"project": project})["project_name"], "Updated automation project")
        child = execute("add_subtask", {"parent": task, "subject": "Child work"})
        self.assertEqual(frappe.db.get_value("Task", child["name"], "parent_task"), task)
        item = execute("add_checklist_item", {"task": task, "item": "Review"})
        execute("set_checklist_item", {"name": item["name"], "is_done": True})
        self.assertEqual(frappe.db.get_value("Pulse Checklist", item["name"], "is_done"), 1)
        execute("bulk_update_tasks", {"tasks": [task, child["name"]], "fields": {"priority": "High"}})
        self.assertEqual(frappe.db.get_value("Task", child["name"], "priority"), "High")
        dependency = execute("add_dependency", {"task": child["name"], "depends_on": task})
        execute("remove_dependency", {"name": dependency["name"]})
        self.assertFalse(frappe.db.exists("Pulse Dependency", dependency["name"]))
        module = execute("create_module", {"project": project, "title": "Delivery", "description": "Keep description"})
        execute("update_module", {"name": module["name"], "fields": {"title": "Release"}})
        self.assertEqual(execute("get_module", {"name": module["name"]})["description"], "Keep description")
        execute("add_module_tasks", {"name": module["name"], "tasks": [task, child["name"]]})
        execute("remove_module_tasks", {"name": module["name"], "tasks": [child["name"]]})
        self.assertEqual(frappe.db.count("Pulse Module Task", {"module": module["name"]}), 1)
        self.assertEqual(len(execute("list_modules", {"project": project})), 1)
        execute("archive_task", {"task": task})
        execute("restore_task", {"task": task})
        self.assertEqual(frappe.db.get_value("Task", task, "pulse_archived"), 0)
        self.assertTrue(frappe.db.exists("Pulse Checklist", item["name"]))
        self.assertIn(task, [row["name"] for row in execute("find_tasks", {"project": project, "q": "Automation"})])

    def test_pages_requests_and_stale_update_rejection(self):
        project = self.project["name"]
        page = execute("create_page", {"project": project, "title": "Automation brief", "content": "<p>Keep body</p>", "tasks": [self.task["name"]]})
        updated = execute("update_page", {"name": page["name"], "modified": str(page["modified"]), "fields": {"title": "Updated brief"}})
        self.assertIn("Keep body", updated["content"])
        with self.assertRaises(frappe.TimestampMismatchError):
            execute("update_page", {"name": page["name"], "modified": "2000-01-01", "fields": {"title": "Stale"}})
        execute("add_page_comment", {"name": page["name"], "content": "Reviewed"})
        self.assertEqual(len(execute("get_page", {"name": page["name"]})["comments"]), 1)
        self.assertEqual(len(execute("list_pages", {"project": project, "query": "Updated brief"})), 1)
        request = execute("create_request", {"project": project, "title": "New delivery", "reviewer": "Administrator"})
        execute("review_request", {"name": request["name"], "status": "Deferred", "note": "Awaiting approval"})
        accepted = execute("accept_request", {"name": request["name"], "note": "Approved"})
        self.assertEqual(execute("get_request", {"name": request["name"]})["status"], "Accepted")
        self.assertEqual(len(execute("list_requests", {"project": project})), 1)
        self.assertTrue(accepted)

    def test_actions_do_not_allow_hidden_records_or_privileged_fields(self):
        user = "automation-scope-" + frappe.generate_hash(length=8) + "@example.test"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": "Action reader", "send_welcome_email": 0,
                        "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        with self.assertRaises(frappe.ValidationError):
            execute("update_project", {"project": self.project["name"], "fields": {"owner": user}})
        frappe.set_user(user)
        for action, values in [("get_project", {"project": self.project["name"]}),
                               ("archive_task", {"task": self.task["name"]}),
                               ("create_page", {"project": self.project["name"], "title": "Forbidden"})]:
            with self.assertRaises(frappe.PermissionError):
                execute(action, values)
