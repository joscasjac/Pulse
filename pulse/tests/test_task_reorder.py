"""Real ORM checks for drag ordering, native status validation and atomicity."""
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api.tasks import move_task


class TestTaskReorder(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_default_company
        self.project = frappe.get_doc({"doctype": "Project", "project_name": "Ordering " + frappe.generate_hash(length=8),
                                       "company": ensure_default_company()}).insert()
        self.tasks = [frappe.get_doc({"doctype": "Task", "subject": f"Order {i}", "project": self.project.name,
                                    "workflow_state": "To Do", "pulse_rank": 0}).insert() for i in range(3)]

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def ordered(self, state="To Do"):
        return frappe.get_all("Task", filters={"project": self.project.name, "workflow_state": state},
                              pluck="name", order_by="pulse_rank asc, modified desc, name asc")

    def test_reorders_equal_ranks_and_preserves_neighbor_modified(self):
        first, second, third = self.tasks
        modified = frappe.db.get_value("Task", third.name, "modified")
        move_task(first.name, "To Do", before=third.name)
        self.assertEqual(self.ordered(), [first.name, third.name, second.name])
        move_task(first.name, "To Do", after=second.name)
        self.assertEqual(self.ordered(), [third.name, second.name, first.name])
        self.assertEqual(frappe.db.get_value("Task", third.name, "modified"), modified)

    def test_cross_status_uses_native_status_and_appends(self):
        first, second, _ = self.tasks
        move_task(first.name, "Done")
        move_task(second.name, "Done")
        self.assertEqual(self.ordered("Done"), [first.name, second.name])
        self.assertEqual(frappe.db.get_value("Task", first.name, "status"), "Completed")

    def test_invalid_anchor_leaves_order_and_state_unchanged(self):
        first, second, _ = self.tasks
        original = self.ordered()
        with self.assertRaises(frappe.ValidationError):
            move_task(first.name, "In Progress", before=second.name)
        self.assertEqual(self.ordered(), original)
        self.assertEqual(frappe.db.get_value("Task", first.name, "workflow_state"), "To Do")

    def test_dependency_failure_leaves_ranks_and_native_state_unchanged(self):
        first, second, _ = self.tasks
        first.append("depends_on", {"task": second.name})
        first.save()
        original = self.ordered()
        with self.assertRaises(frappe.ValidationError):
            move_task(first.name, "Done")
        self.assertEqual(self.ordered(), original)
        self.assertEqual(frappe.db.get_value("Task", first.name, "status"), "Open")

    def test_hidden_anchor_and_task_are_denied(self):
        user = "reorder-" + frappe.generate_hash(length=8) + "@example.com"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": "Reorder",
                        "send_welcome_email": 0, "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        visible = frappe.get_doc({"doctype": "Project", "project_name": "Visible " + frappe.generate_hash(length=8),
                                  "company": self.project.company, "users": [{"user": user, "welcome_email_sent": 1}]}).insert()
        task = frappe.get_doc({"doctype": "Task", "subject": "Visible", "project": visible.name,
                               "workflow_state": "To Do"}).insert()
        frappe.set_user(user)
        with self.assertRaises(frappe.PermissionError):
            move_task(self.tasks[0].name, "To Do")
        with self.assertRaises(frappe.PermissionError):
            move_task(task.name, "To Do", before=self.tasks[0].name)
