"""Real Frappe integration checks for project vocabulary and bulk atomicity."""
import frappe
from frappe.tests import IntegrationTestCase


class TestTaskFlexibility(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_default_company
        company = ensure_default_company()
        self.project = frappe.get_doc({"doctype": "Project", "project_name": "Task config " + frappe.generate_hash(length=8), "company": company}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_custom_status_and_labels_survive_native_task_save(self):
        from pulse.api.task_config import save_config, save_label
        save_config(self.project.name, [{"label": "Queued", "category": "To Do", "color": "#123456"},
                                        {"label": "Delivered", "category": "Done", "color": "#654321"}])
        label = save_label(self.project.name, "Client", "#abcdef")
        task = frappe.get_doc({"doctype": "Task", "subject": "Flexible", "project": self.project.name,
                               "workflow_state": "Delivered", "expected_time": 4, "pulse_story_points": 3,
                               "pulse_labels": [{"label": label["name"]}]}).insert()
        self.assertEqual(task.status, "Completed")
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.pulse_labels[0].label, label["name"])
        with self.assertRaises(frappe.ValidationError):
            save_config(self.project.name, [{"label": "Queued", "category": "To Do", "color": "#123456"}])

    def test_bulk_validation_failure_rolls_back_previous_task(self):
        from pulse.api.tasks import bulk_update
        other = frappe.get_doc({"doctype": "Project", "project_name": "Restricted vocabulary " + frappe.generate_hash(length=8),
                                "company": self.project.company,
                                "pulse_task_statuses": [{"label": "Queued", "category": "To Do", "color": "#123456"}]}).insert()
        first = frappe.get_doc({"doctype": "Task", "subject": "First", "project": self.project.name,
                                "workflow_state": "To Do"}).insert()
        second = frappe.get_doc({"doctype": "Task", "subject": "Second", "project": other.name,
                                 "workflow_state": "Queued"}).insert()
        with self.assertRaises(frappe.ValidationError):
            bulk_update([first.name, second.name], {"workflow_state": "In Progress"})
        self.assertEqual(frappe.db.get_value("Task", first.name, "workflow_state"), "To Do")
        self.assertEqual(frappe.db.get_value("Task", second.name, "workflow_state"), "Queued")

    def test_custom_completion_respects_native_dependencies(self):
        dependency = frappe.get_doc({"doctype": "Task", "subject": "Prerequisite", "project": self.project.name}).insert()
        task = frappe.get_doc({"doctype": "Task", "subject": "Dependent", "project": self.project.name,
                               "depends_on": [{"task": dependency.name}]}).insert()
        task.workflow_state = "Done"
        with self.assertRaises(frappe.ValidationError):
            task.save()
        self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Open")

    def test_archive_keeps_task_and_its_children(self):
        from pulse.api.tasks import bulk_update
        from pulse.api.spa import get_board
        task = frappe.get_doc({"doctype": "Task", "subject": "Archive", "project": self.project.name}).insert()
        item = frappe.get_doc({"doctype": "Pulse Checklist", "task": task.name, "item": "Keep this"}).insert()
        bulk_update([task.name], {"pulse_archived": 1})
        self.assertTrue(frappe.db.exists("Task", task.name))
        self.assertTrue(frappe.db.exists("Pulse Checklist", item.name))
        self.assertEqual(get_board(project=self.project.name)["total"], 0)
        self.assertEqual(get_board(project=self.project.name, include_archived=1)["total"], 1)
