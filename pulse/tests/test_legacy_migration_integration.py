"""Opt-in real ORM migration rehearsal on a disposable ERPNext test site only.

Requires site config pulse_legacy_migration_tests=1. Never runs on a site with
any of the original legacy DocTypes. Schemas are projected from e9a3bd2; see
fixtures/legacy_migration/README.md. Migration commit is intercepted so test
records remain in the test transaction; all validation and SQL use real Frappe.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from pulse import erpnext_bridge as bridge


class TestLegacyMigrationRehearsal(IntegrationTestCase):
    legacy = ("Pulse Project User", "Pulse Issue Type", "Pulse Project", "Pulse Task")
    created = []

    @classmethod
    def setUpClass(cls):
        if not frappe.conf.get("pulse_legacy_migration_tests"):
            raise unittest.SkipTest("Requires disposable site with pulse_legacy_migration_tests=1")
        if any(frappe.db.exists("DocType", dt) for dt in cls.legacy):
            raise unittest.SkipTest("Refusing to modify a site with existing legacy DocTypes")
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.created = []
        try:
            for dt in cls.legacy:
                path = Path(__file__).parent / "fixtures" / "legacy_migration" / (dt.lower().replace(" ", "_") + ".json")
                frappe.get_doc(json.loads(path.read_text())).insert(ignore_permissions=True)
                cls.created.append(dt)
            frappe.db.commit()  # Fixture DDL is outside every test transaction.
        except Exception:
            cls._remove_owned_schemas()
            raise

    @classmethod
    def _remove_owned_schemas(cls):
        for dt in reversed(cls.created):
            if frappe.db.exists("DocType", dt):
                frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)
        frappe.db.commit()
        cls.created = []

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        cls._remove_owned_schemas()
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")
        self.suffix = frappe.generate_hash(length=8)
        self.issue_type = frappe.get_doc({"doctype": "Pulse Issue Type", "issue_type_name": "Legacy " + self.suffix}).insert()
        self.project = frappe.get_doc({"doctype": "Pulse Project", "project_name": "Legacy " + self.suffix,
            "pulse_project_key": "LM" + self.suffix.upper(), "users": [{"user": "Administrator"}]}).insert()
        self.parent = frappe.get_doc({"doctype": "Pulse Task", "subject": "Legacy parent", "project": self.project.name,
                                      "task_type": self.issue_type.name}).insert()
        self.child = frappe.get_doc({"doctype": "Pulse Task", "subject": "Legacy child", "project": self.project.name,
            "parent_task": self.parent.name, "pulse_epic": self.parent.name, "description": "Preserve detail",
            "pulse_story_points": 5, "exp_start_date": "2026-01-01", "exp_end_date": "2026-01-02"}).insert()
        frappe.db.set_value("Pulse Task", self.child.name, "_assign", '["Administrator"]')
        self.todo = frappe.get_doc({"doctype": "ToDo", "reference_type": "Pulse Task", "reference_name": self.parent.name,
                                    "allocated_to": "Administrator", "description": "Existing assignment"}).insert()
        self.comment = self.child.add_comment("Comment", "Historical comment")
        # db_insert represents rows already stored before Link options changed in
        # the upgrade. Normal inserts correctly reject old IDs after migration.
        self.checklist = self._stored("Pulse Checklist", task=self.child.name, item="Keep this", is_done=1)
        self.dependency = self._stored("Pulse Dependency", source_task=self.parent.name, target_task=self.child.name,
            source_project=self.project.name, target_project=self.project.name, dependency_type="Finish-to-Start", status="Active")
        self.file = self._stored("File", file_name="legacy-proof.txt", file_url="https://example.invalid/legacy-proof.txt",
            attached_to_doctype="Pulse Task", attached_to_name=self.child.name, is_private=1)

    def _stored(self, doctype, **fields):
        doc = frappe.get_doc({"doctype": doctype, "name": frappe.generate_hash(length=12), **fields})
        doc.db_insert()
        return doc

    def tearDown(self):
        frappe.db.rollback()

    def apply(self):
        with patch.object(frappe.db, "commit") as commit:
            result = bridge.migrate(dry_run=False)
            commit.assert_called_once()
        return result

    def test_source_and_all_relationships_survive_idempotent_no_key_migration(self):
        self.assertFalse(self.parent.issue_key)
        result = self.apply()
        project = result["projects"][self.project.name]
        parent, child = (result["tasks"][doc.name] for doc in (self.parent, self.child))
        native = frappe.get_doc("Task", child)
        self.assertEqual(native.parent_task, parent)
        self.assertEqual(native.pulse_epic, parent)
        self.assertEqual(native.project, project)
        self.assertEqual(native.description, "Preserve detail")
        self.assertEqual(native.pulse_story_points, 5)
        self.assertTrue(frappe.db.get_value("Task", parent, "is_group"))
        self.assertEqual(frappe.db.get_value("Task", parent, "type"), self.issue_type.name)
        self.assertTrue(frappe.db.exists("Project User", {"parent": project, "user": "Administrator"}))
        self.assertEqual(frappe.db.get_value("Pulse Checklist", self.checklist.name, "task"), child)
        self.assertEqual(frappe.db.get_value("Pulse Dependency", self.dependency.name, ["source_task", "target_task", "source_project", "target_project"]), (parent, child, project, project))
        self.assertEqual(frappe.db.get_value("File", self.file.name, ["attached_to_doctype", "attached_to_name"]), ("Task", child))
        self.assertEqual(frappe.db.get_value("Comment", self.comment.name, ["reference_doctype", "reference_name"]), ("Task", child))
        self.assertEqual(frappe.db.get_value("ToDo", self.todo.name, ["reference_type", "reference_name"]), ("Task", parent))
        self.assertEqual(frappe.db.count("ToDo", {"reference_type": "Task", "reference_name": child, "allocated_to": "Administrator", "status": "Open"}), 1)
        second = self.apply()
        self.assertEqual(result, second)
        self.assertEqual(frappe.db.count("Task", {"pulse_legacy_task": self.child.name}), 1)
        self.assertEqual(frappe.db.count("ToDo", {"reference_type": "Task", "reference_name": child, "status": "Open"}), 1)
        source = frappe.get_doc("Pulse Task", self.child.name)
        self.assertEqual(source.parent_task, self.parent.name)
        self.assertEqual(source.project, self.project.name)
        self.assertEqual(source.description, native.description)
        self.assertTrue(frappe.db.exists("Pulse Project User", {"parent": self.project.name, "user": "Administrator"}))

    def test_rehearsal_rolls_back_native_records_and_reference_changes(self):
        result = bridge.migrate()
        self.assertTrue(result["dry_run"])
        self.assertFalse(frappe.db.exists("Task", {"pulse_legacy_task": self.child.name}))
        self.assertFalse(frappe.db.exists("Project", {"pulse_legacy_project": self.project.name}))
        self.assertEqual(frappe.db.get_value("Pulse Checklist", self.checklist.name, "task"), self.child.name)
        self.assertEqual(frappe.db.get_value("File", self.file.name, "attached_to_doctype"), "Pulse Task")
        self.assertTrue(frappe.db.exists("Pulse Task", self.child.name))

    def test_validation_failure_rolls_back_and_restores_flags(self):
        previous = dict(frappe.flags)
        with patch.object(bridge, "_validate_migration", side_effect=frappe.ValidationError("Injected final validation failure")):
            with self.assertRaises(frappe.ValidationError):
                bridge.migrate(dry_run=False)
        for key in ("mute_emails", "mute_messages", "in_import", "pulse_migration"):
            self.assertEqual(frappe.flags.get(key), previous.get(key))
            self.assertEqual(key in frappe.flags, key in previous)
        self.assertFalse(frappe.db.exists("Task", {"pulse_legacy_task": self.child.name}))
        self.assertEqual(frappe.db.get_value("Comment", self.comment.name, "reference_doctype"), "Pulse Task")
        self.assertEqual(frappe.db.get_value("ToDo", self.todo.name, "reference_type"), "Pulse Task")
