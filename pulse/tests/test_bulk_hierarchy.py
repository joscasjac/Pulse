"""Atomic bulk project moves preserve the native Task parent/child hierarchy."""
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api.tasks import bulk_update


class TestBulkHierarchy(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_default_company
        company = ensure_default_company()
        self.source, self.destination = [frappe.get_doc({"doctype": "Project", "project_name": "Hierarchy " + frappe.generate_hash(length=8),
                                                        "company": company}).insert() for _ in range(2)]
        self.parent = self.make_task("Parent", is_group=1)
        self.child = self.make_task("Child", parent_task=self.parent.name, is_group=1)
        self.leaf = self.make_task("Leaf", parent_task=self.child.name)

    def make_task(self, subject, **fields):
        return frappe.get_doc({"doctype": "Task", "subject": subject, "project": self.source.name,
                               "workflow_state": "To Do", **fields}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def assert_source(self):
        for doc in (self.parent, self.child, self.leaf):
            self.assertEqual(frappe.db.get_value("Task", doc.name, "project"), self.source.name)

    def test_child_first_selection_moves_complete_hierarchy(self):
        names = [self.leaf.name, self.child.name, self.parent.name]
        result = bulk_update(names, {"project": self.destination.name})
        self.assertEqual(result["updated"], names)
        for doc in (self.parent, self.child, self.leaf):
            self.assertEqual(frappe.db.get_value("Task", doc.name, "project"), self.destination.name)
        self.assertEqual(frappe.db.get_value("Task", self.leaf.name, "parent_task"), self.child.name)
        self.assertEqual(frappe.db.get_value("Task", self.child.name, "parent_task"), self.parent.name)

    def test_partial_parent_move_is_rejected_before_any_edits(self):
        unrelated = self.make_task("Unrelated")
        with self.assertRaises(frappe.ValidationError):
            bulk_update([unrelated.name, self.parent.name], {"project": self.destination.name, "priority": "High"})
        self.assert_source()
        self.assertEqual(frappe.db.get_value("Task", unrelated.name, "project"), self.source.name)
        self.assertNotEqual(frappe.db.get_value("Task", unrelated.name, "priority"), "High")

    def test_move_preserves_relations_and_refreshes_dependency_projects(self):
        prerequisite = self.make_task("External prerequisite")
        self.leaf.append("depends_on", {"task": prerequisite.name})
        self.leaf.save()
        dependency = frappe.get_doc({"doctype": "Pulse Dependency",
            "source_task": self.leaf.name, "target_task": prerequisite.name}).insert()
        incoming = frappe.get_doc({"doctype": "Pulse Dependency",
            "source_task": prerequisite.name, "target_task": self.parent.name}).insert()
        checklist = frappe.get_doc({"doctype": "Pulse Checklist", "task": self.leaf.name,
                                   "item": "Retain checklist"}).insert()
        comment = self.leaf.add_comment("Comment", "Retain comment")
        bulk_update([self.leaf.name, self.child.name, self.parent.name],
                    {"project": self.destination.name})
        self.leaf.reload()
        self.assertEqual(self.leaf.parent_task, self.child.name)
        self.assertEqual(self.leaf.depends_on[0].task, prerequisite.name)
        self.assertEqual(frappe.db.get_value("Pulse Checklist", checklist.name, "task"), self.leaf.name)
        self.assertEqual(frappe.db.get_value("Comment", comment.name, "reference_name"), self.leaf.name)
        dependency.reload(); incoming.reload()
        self.assertEqual(dependency.source_project, self.destination.name)
        self.assertEqual(dependency.target_project, self.source.name)
        self.assertEqual(incoming.source_project, self.source.name)
        self.assertEqual(incoming.target_project, self.destination.name)

    def test_partial_child_move_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            bulk_update([self.leaf.name, self.child.name], {"project": self.destination.name})
        self.assert_source()

    def test_missing_grandchild_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            bulk_update([self.parent.name, self.child.name], {"project": self.destination.name})
        self.assert_source()

    def test_late_validation_failure_rolls_back_parent_move(self):
        from pulse.api.task_config import save_config, statuses_for
        prerequisite = self.make_task("Retained prerequisite")
        dependency = frappe.get_doc({"doctype": "Pulse Dependency",
            "source_task": self.parent.name, "target_task": prerequisite.name}).insert()
        self.leaf.reload()
        self.leaf.type = "Bug"
        self.leaf.save()
        save_config(self.destination.name, statuses_for(self.destination.name), ["Task"])
        # Parent and child save first; only the leaf has a type the target rejects.
        with self.assertRaises(frappe.ValidationError):
            bulk_update([self.leaf.name, self.child.name, self.parent.name],
                        {"project": self.destination.name})
        self.assert_source()
        dependency.reload()
        self.assertEqual(dependency.source_project, self.source.name)

    def test_direct_native_move_refreshes_dependency_project(self):
        task = self.make_task("Native move")
        dependency = frappe.get_doc({"doctype": "Pulse Dependency",
            "source_task": self.leaf.name, "target_task": task.name}).insert()
        task.project = self.destination.name
        task.save()
        dependency.reload()
        self.assertEqual(dependency.source_project, self.source.name)
        self.assertEqual(dependency.target_project, self.destination.name)

    def test_existing_dependency_projects_repaired_idempotently(self):
        from pulse.install import repair_dependency_projects
        dependency = frappe.get_doc({"doctype": "Pulse Dependency",
            "source_task": self.leaf.name, "target_task": self.parent.name}).insert()
        modified = frappe.utils.get_datetime(dependency.modified)
        frappe.db.set_value("Pulse Dependency", dependency.name,
                            {"source_project": self.destination.name, "target_project": None},
                            update_modified=False)
        for _ in range(2):
            repair_dependency_projects()
            dependency.reload()
            self.assertEqual(dependency.source_project, self.source.name)
            self.assertEqual(dependency.target_project, self.source.name)
            self.assertEqual(dependency.modified, modified)
            self.assertEqual(dependency.source_task, self.leaf.name)
            self.assertEqual(dependency.target_task, self.parent.name)

    def test_direct_parent_project_edit_cannot_strand_children(self):
        self.parent.reload()
        self.parent.project = self.destination.name
        with self.assertRaises(frappe.ValidationError):
            self.parent.save()
        self.assert_source()

    def test_bulk_move_context_cleared_after_failure(self):
        from pulse.api.task_config import save_config, statuses_for
        self.leaf.reload()
        self.leaf.type = "Bug"
        self.leaf.save()
        save_config(self.destination.name, statuses_for(self.destination.name), ["Task"])
        with self.assertRaises(frappe.ValidationError):
            bulk_update([self.leaf.name, self.child.name, self.parent.name], {"project": self.destination.name})
        self.assertFalse(frappe.flags.get("pulse_pending_task_projects"))
        self.parent.reload()
        self.parent.project = self.destination.name
        with self.assertRaises(frappe.ValidationError):
            self.parent.save()
        self.assert_source()
