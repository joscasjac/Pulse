"""Run with bench --site SITE run-tests --app pulse --module pulse.tests.test_permissions_integration.

Real ORM regression checks: role permissions, membership query hooks, document
hooks and whitelisted endpoints must agree. Requires ERPNext and migrated Pulse.
"""
import frappe
from frappe.tests import IntegrationTestCase


class TestPermissionBoundaries(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8)
        self.user = f"pulse-security-{self.suffix}@example.com"
        frappe.get_doc({"doctype": "User", "email": self.user, "first_name": "Permission Test",
                        "send_welcome_email": 0, "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        from pulse.erpnext_bridge import ensure_default_company
        company = ensure_default_company()
        self.visible = frappe.get_doc({"doctype": "Project", "project_name": "Visible " + self.suffix,
                                       "company": company, "users": [{"user": self.user, "welcome_email_sent": 1}]}).insert()
        self.hidden = frappe.get_doc({"doctype": "Project", "project_name": "Hidden " + self.suffix,
                                      "company": company}).insert()
        self.visible_task = frappe.get_doc({"doctype": "Task", "subject": "Visible task",
                                            "project": self.visible.name}).insert()
        self.hidden_task = frappe.get_doc({"doctype": "Task", "subject": "Secret task",
                                           "project": self.hidden.name}).insert()
        self.item = frappe.get_doc({"doctype": "Pulse Checklist", "task": self.hidden_task.name,
                                   "item": "Private checklist", "is_done": 0}).insert()
        frappe.set_user(self.user)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_list_board_search_and_detail_agree(self):
        from pulse.api import spa
        tasks = frappe.get_list("Task", pluck="name", limit_page_length=0)
        self.assertIn(self.visible_task.name, tasks)
        self.assertNotIn(self.hidden_task.name, tasks)
        with self.assertRaises(frappe.PermissionError):
            spa.get_board(project=self.hidden.name)
        self.assertEqual(spa.search_tasks(project=self.hidden.name), [])
        with self.assertRaises(frappe.PermissionError):
            spa.get_task(self.hidden_task.name)
        with self.assertRaises(frappe.PermissionError):
            spa.get_entity("Task", self.hidden_task.name)
        with self.assertRaises(frappe.PermissionError):
            spa.list_attachments(self.hidden_task.name)

    def test_related_writes_cannot_escape_task_scope(self):
        from pulse.api import spa
        for action in (
            lambda: spa.add_comment(self.hidden_task.name, "unauthorized"),
            lambda: spa.toggle_checklist_item(self.item.name, 1),
            lambda: spa.assign_task(self.hidden_task.name, self.user),
            lambda: spa.add_dependency(self.visible_task.name, self.hidden_task.name),
            lambda: spa.delete_task(self.hidden_task.name),
        ):
            with self.assertRaises(frappe.PermissionError):
                action()
        self.assertEqual(frappe.db.get_value("Pulse Checklist", self.item.name, "is_done"), 0)
        self.assertTrue(frappe.db.exists("Task", self.hidden_task.name))

    def test_no_membership_does_not_grant_global_access(self):
        frappe.set_user("Administrator")
        self.visible.reload()
        self.visible.set("users", [])
        self.visible.save()
        frappe.set_user(self.user)
        self.assertEqual(frappe.get_list("Task", filters={"name": ["in", [self.visible_task.name, self.hidden_task.name]]}, pluck="name"), [])

    def test_native_dependency_write_requires_target_visibility(self):
        task = frappe.get_doc("Task", self.visible_task.name)
        task.append("depends_on", {"task": self.hidden_task.name})
        with self.assertRaises(frappe.PermissionError):
            task.save()
        self.assertFalse(frappe.db.exists("Task Depends On", {
            "parent": task.name, "task": self.hidden_task.name}))

    def test_existing_hidden_dependency_does_not_block_unrelated_edits(self):
        frappe.set_user("Administrator")
        task = frappe.get_doc("Task", self.visible_task.name)
        task.append("depends_on", {"task": self.hidden_task.name})
        task.save()
        frappe.set_user(self.user)
        task = frappe.get_doc("Task", task.name)
        task.subject = "Updated visible task"
        task.save()
        self.assertEqual(frappe.db.get_value("Task", task.name, "subject"), "Updated visible task")
        self.assertTrue(frappe.db.exists("Task Depends On", {
            "parent": task.name, "task": self.hidden_task.name}))

    def test_native_dependency_accepts_visible_target(self):
        from pulse.api.spa import get_entity
        target = frappe.get_doc({"doctype": "Task", "subject": "Visible prerequisite",
                                "project": self.visible.name}).insert()
        task = frappe.get_doc("Task", self.visible_task.name)
        task.append("depends_on", {"task": target.name})
        task.save()
        self.assertTrue(frappe.db.exists("Task Depends On", {"parent": task.name, "task": target.name}))
        result = get_entity("Task", task.name)
        self.assertEqual([row["task"] for row in result["depends_on"]], [target.name])
        self.assertIn(target.name, result["depends_on_tasks"])

    def test_generic_task_read_hides_unreadable_dependency_details(self):
        from pulse.api.spa import get_entity
        frappe.set_user("Administrator")
        task = frappe.get_doc("Task", self.visible_task.name)
        task.append("depends_on", {"task": self.hidden_task.name, "subject": "Secret task"})
        task.save()
        frappe.set_user(self.user)
        result = get_entity("Task", task.name)
        self.assertEqual(result.get("depends_on"), [])
        self.assertNotIn(self.hidden_task.name, result.get("depends_on_tasks") or "")
        self.assertEqual(result["subject"], "Visible task")
        self.assertTrue(frappe.db.exists("Task Depends On", {
            "parent": task.name, "task": self.hidden_task.name}))

    def test_dependency_and_legacy_time_do_not_leak_through_generic_reads(self):
        frappe.set_user("Administrator")
        dependency = frappe.get_doc({"doctype": "Pulse Dependency", "source_task": self.visible_task.name,
                                     "target_task": self.hidden_task.name}).insert()
        legacy = frappe.get_doc({"doctype": "Pulse Timesheet", "user": self.user,
                                "week_starting": "2026-09-14", "entries": [{"date": "2026-09-14",
                                "task": self.hidden_task.name, "project": self.hidden.name, "hours": 1}]}).insert(ignore_permissions=True)
        frappe.set_user(self.user)
        from pulse.api.spa import get_entity
        for doctype, name in (("Pulse Dependency", dependency.name), ("Pulse Timesheet", legacy.name)):
            self.assertEqual(frappe.get_list(doctype, filters={"name": name}, pluck="name"), [])
            with self.assertRaises(frappe.PermissionError):
                get_entity(doctype, name)

    def test_native_task_read_filters_private_links_and_roundtrip_preserves_them(self):
        from frappe.client import get
        from frappe.api.v1 import read_doc
        frappe.set_user("Administrator")
        task = frappe.get_doc("Task", self.visible_task.name)
        task.append("depends_on", {"task": self.hidden_task.name, "subject": "Secret task"})
        task.save()
        private_row = task.depends_on[0].name
        frappe.set_user(self.user)
        result = get("Task", task.name)
        self.assertEqual(result.get("depends_on"), [])
        self.assertNotIn(self.hidden_task.name, result.get("depends_on_tasks") or "")
        resource = read_doc("Task", task.name).as_dict()
        self.assertEqual(resource.get("depends_on"), [])
        result["subject"] = "Safe roundtrip edit"
        frappe.get_doc(result).save()
        stored = frappe.get_doc("Task", task.name)
        self.assertEqual(stored.subject, "Safe roundtrip edit")
        self.assertEqual([(row.name, row.task) for row in stored.depends_on],
                         [(private_row, self.hidden_task.name)])

    def test_native_roundtrip_can_remove_visible_dependency_while_retaining_private_one(self):
        from frappe.client import get
        frappe.set_user("Administrator")
        target = frappe.get_doc({"doctype": "Task", "subject": "Readable prerequisite",
                                "project": self.visible.name}).insert()
        task = frappe.get_doc("Task", self.visible_task.name)
        task.append("depends_on", {"task": target.name})
        task.append("depends_on", {"task": self.hidden_task.name})
        task.save()
        frappe.set_user(self.user)
        result = get("Task", task.name)
        self.assertEqual([row.task for row in result.depends_on], [target.name])
        result["depends_on"] = []
        frappe.get_doc(result).save()
        self.assertEqual([row.task for row in frappe.get_doc("Task", task.name).depends_on],
                         [self.hidden_task.name])
        frappe.set_user("Administrator")
        task = frappe.get_doc("Task", task.name)
        task.set("depends_on", [])
        task.save()
        self.assertFalse(frappe.get_doc("Task", task.name).depends_on)
