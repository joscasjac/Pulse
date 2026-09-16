"""Real native Task rich content and assignment history regressions."""
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase


class TestTaskRichActivity(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_default_company
        suffix = frappe.generate_hash(length=8)
        self.project = frappe.get_doc({"doctype": "Project", "project_name": "Rich activity " + suffix,
                                       "company": ensure_default_company()}).insert()
        self.task = frappe.get_doc({"doctype": "Task", "subject": "Rich content", "priority": "Low", "project": self.project.name}).insert()
        self.user = "pulse-activity-" + suffix + "@example.com"
        frappe.get_doc({"doctype": "User", "email": self.user, "first_name": "Activity Reader",
                        "send_welcome_email": 0, "roles": [{"role": "Pulse Senior Developer"}]}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_rich_description_preserves_code_image_and_mention_and_records_changes(self):
        from pulse.api.tasks import activity
        from pulse.api.spa import update_task
        content = ('<p>Review <span class="mention" data-type="mention" data-id="Administrator" '
                   'data-label="Administrator">@Administrator</span></p>'
                   '<pre><code class="language-python">print(&quot;hello&quot;)</code></pre>'
                   '<p><img src="/private/files/pulse-test.png" alt="Example"></p>')
        # Frappe disables Version records in tests; restore production save behavior.
        with patch.object(frappe, "in_test", False), patch.object(frappe.db, "commit"):
            update_task(self.task.name, description=content, priority="High")
        self.task.reload()
        self.assertIn('<pre><code', self.task.description)
        self.assertIn('/private/files/pulse-test.png', self.task.description)
        self.assertIn('data-id="Administrator"', self.task.description)
        changed = [change for entry in activity(self.task.name) for change in entry["changed"]]
        self.assertIn(["priority", "Low", "High"], changed)
        self.assertTrue(any(change[0] == "description" and 'print(' in change[2] for change in changed))

    def test_mention_suggestions_require_task_read_and_ignore_assignment_rank(self):
        from pulse.api.tasks import mention_options
        from pulse.services.hierarchy_service import can_assign
        # An outsider cannot use the endpoint as a directory lookup.
        frappe.set_user(self.user)
        with self.assertRaises(frappe.PermissionError):
            mention_options(self.task.name)
        frappe.set_user("Administrator")
        self.project.reload()
        self.project.append("users", {"user": self.user, "welcome_email_sent": 1})
        suffix = frappe.generate_hash(length=8)
        junior = "mention-junior-" + suffix + "@example.com"
        disabled = "mention-disabled-" + suffix + "@example.com"
        for email, role in ((junior, "Pulse Junior Developer"), (disabled, "Pulse Senior Developer")):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "Mention candidate",
                            "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
            self.project.append("users", {"user": email, "welcome_email_sent": 1})
        self.project.save()
        frappe.db.set_value("User", disabled, "enabled", 0)
        frappe.set_user(self.user)
        self.assertFalse(can_assign(self.user, "Administrator"))
        options = {row["id"]: row for row in mention_options(self.task.name)}
        self.assertIn("Administrator", options)
        self.assertIn(self.user, options)
        self.assertNotIn(junior, options)  # Membership alone is insufficient for juniors.
        self.assertNotIn(disabled, options)
        self.assertEqual(options[self.user]["label"], "Activity Reader")
        # Recheck permissions on each request rather than caching recipient lists.
        frappe.set_user("Administrator")
        self.project.reload()
        self.project.set("users", [])
        self.project.save()
        self.assertNotIn(self.user, {row["id"] for row in mention_options(self.task.name)})

    def test_description_mentions_notify_only_readers_and_only_when_added(self):
        from pulse.api.tasks import bulk_update
        self.project.reload()
        self.project.append("users", {"user": self.user, "welcome_email_sent": 1})
        self.project.save()
        outsider = "mention-outsider-" + frappe.generate_hash(length=8) + "@example.com"
        frappe.get_doc({"doctype": "User", "email": outsider, "first_name": "Outside reader",
                        "send_welcome_email": 0, "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        self.assertTrue(frappe.has_permission("Task", "read", doc=self.task, user=self.user))
        self.assertFalse(frappe.has_permission("Task", "read", doc=self.task, user=outsider))
        content = "<p>Review " + " ".join(
            f'<span class="mention" data-type="mention" data-id="{user}">@Reader</span>'
            for user in (self.user, outsider)) + "</p>"
        bulk_update([self.task.name], {"description": content})
        filters = {"reference_doctype": "Task", "reference_name": self.task.name,
                   "notification_type": "Mention"}
        self.assertEqual(frappe.get_all("Pulse Notification", filters=filters, pluck="recipient"), [self.user])
        bulk_update([self.task.name], {"description": content + "<p>More detail.</p>"})
        self.assertEqual(frappe.db.count("Pulse Notification", filters), 1)

    def test_assignment_api_is_idempotent_and_native_removal_is_recorded_once(self):
        from pulse.api.spa import assign_task, unassign_task
        from pulse.api.tasks import activity
        with patch.object(frappe.db, "commit"):
            assign_task(self.task.name, self.user)
            assign_task(self.task.name, self.user)
            unassign_task(self.task.name, self.user)
        descriptions = [row.get("description") for row in activity(self.task.name)]
        self.assertEqual(descriptions.count("Assigned " + self.user), 1)
        self.assertEqual(descriptions.count("Unassigned " + self.user), 1)

    def test_deleting_open_native_assignment_records_removal(self):
        from pulse.api.tasks import activity
        todo = frappe.get_doc({"doctype": "ToDo", "reference_type": "Task", "reference_name": self.task.name,
                               "allocated_to": self.user, "description": "Assigned work", "status": "Open"}).insert()
        todo.delete()
        descriptions = [row.get("description") for row in activity(self.task.name)]
        self.assertEqual(descriptions.count("Unassigned " + self.user), 1)

    def test_history_requires_parent_task_visibility(self):
        from pulse.api.tasks import activity
        frappe.set_user(self.user)
        with self.assertRaises(frappe.PermissionError):
            activity(self.task.name)
