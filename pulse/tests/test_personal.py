"""Private personal navigation and notification boundaries on the real ORM."""
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api import personal


class TestPersonal(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        suffix = frappe.generate_hash(length=8)
        self.user = f"personal-{suffix}@example.com"
        frappe.get_doc({"doctype": "User", "email": self.user, "first_name": "Personal",
                        "send_welcome_email": 0, "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        from pulse.erpnext_bridge import ensure_default_company
        self.project = frappe.get_doc({"doctype": "Project", "project_name": "Personal " + suffix,
            "company": ensure_default_company(), "users": [{"user": self.user, "welcome_email_sent": 1}]}).insert()
        self.task = frappe.get_doc({"doctype": "Task", "subject": "Personal " + suffix,
                                    "project": self.project.name}).insert()
        self.notification = frappe.get_doc({"doctype": "Pulse Notification", "recipient": self.user,
            "reference_doctype": "Task", "reference_name": self.task.name,
            "message": "Private message", "notification_type": "System"}).insert(ignore_permissions=True)
        frappe.set_user(self.user)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_favorite_recent_and_follow_are_independent_and_private(self):
        for kind in ("Favorite", "Recent", "Follow"):
            personal.remember("Task", self.task.name, kind)
        self.assertEqual(set(personal.state("Task", self.task.name)), {"Favorite", "Recent", "Follow"})
        item = frappe.get_doc("Pulse Personal Item", {"user": self.user,
            "reference_doctype": "Task", "reference_name": self.task.name, "kind": "Favorite"})
        self.assertIs(personal.personal_permission(item), True)
        self.assertTrue(frappe.has_permission("Pulse Personal Item", "read", doc=item))
        personal.remember("Task", self.task.name, "Favorite", 0)
        self.assertEqual(set(personal.state("Task", self.task.name)), {"Recent", "Follow"})
        frappe.set_user("Administrator")
        self.assertFalse([row for row in personal.items() if row.reference_name == self.task.name])
        self.assertFalse(frappe.get_list("Pulse Personal Item", filters={"reference_name": self.task.name}, pluck="name"))
        self.assertFalse([row for row in personal.inbox() if row.name == self.notification.name])
        with self.assertRaises(frappe.PermissionError):
            personal.mark_read(self.notification.name)

    def test_revocation_hides_search_inbox_and_direct_rest_lists(self):
        personal.remember("Task", self.task.name, "Favorite")
        self.assertTrue(personal.search(self.task.subject))
        personal.mark_read(self.notification.name, 1)
        self.assertFalse(personal.inbox(1))
        personal.mark_read(self.notification.name, 0)
        self.assertTrue(personal.inbox(1))
        frappe.set_user("Administrator")
        self.project.reload()
        self.project.set("users", [])
        self.project.save()
        frappe.set_user(self.user)
        self.assertFalse(personal.search(self.task.subject))
        self.assertFalse([row for row in personal.items() if row.reference_name == self.task.name])
        self.assertFalse([row for row in personal.inbox() if row.name == self.notification.name])
        self.assertFalse(frappe.get_list("Pulse Notification", filters={"name": self.notification.name}, pluck="name"))
        self.assertFalse(frappe.get_list("Pulse Personal Item", filters={"reference_name": self.task.name}, pluck="name"))
        with self.assertRaises(frappe.PermissionError):
            personal.mark_read(self.notification.name)
        with self.assertRaises(frappe.PermissionError):
            personal.remember("Task", self.task.name)
        self.assertFalse(frappe.has_permission("Pulse Notification", "read", doc=self.notification.name))
