"""Transaction/identity regressions without a live Frappe installation."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch


class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.flags = {"mute_emails": False, "in_import": "previous"}
        def fail(message):
            raise ValueError(message)
        self.frappe = SimpleNamespace(flags=self.flags, db=Mock(), throw=fail)
        self.frappe.db.has_column.return_value = True
        spec = importlib.util.spec_from_file_location("bridge_under_test", Path(__file__).parents[1] / "erpnext_bridge.py")
        self.bridge = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe,
            "frappe.custom.doctype.custom_field.custom_field": SimpleNamespace(create_custom_fields=Mock())}):
            spec.loader.exec_module(self.bridge)
        self.stages = []
        for name, result in (("_migrate_projects", {"oldp": "newp"}), ("_migrate_issue_types", None),
                             ("_migrate_tasks", {"oldt": "newt"}), ("_repoint_retained", None),
                             ("_migrate_assignments", None), ("_validate_migration", None)):
            patcher = patch.object(self.bridge, name, return_value=result)
            self.stages.append(patcher.start())
            self.addCleanup(patcher.stop)

    def test_default_rehearsal_rolls_back_and_restores_flags(self):
        result = self.bridge.migrate()
        self.assertTrue(result["dry_run"])
        self.frappe.db.rollback.assert_called_once_with(save_point="pulse_legacy_migration")
        self.frappe.db.commit.assert_not_called()
        self.assertEqual(self.flags, {"mute_emails": False, "in_import": "previous"})

    def test_apply_commits_only_after_validation(self):
        self.bridge.migrate(dry_run=False)
        self.stages[-1].assert_called_once_with({"oldp": "newp"}, {"oldt": "newt"})
        self.frappe.db.commit.assert_called_once()
        self.frappe.db.rollback.assert_not_called()

    def test_validation_failure_rolls_back_apply_and_restores_flags(self):
        self.stages[-1].side_effect = ValueError("broken reference")
        with self.assertRaisesRegex(ValueError, "broken reference"):
            self.bridge.migrate(dry_run=False)
        self.frappe.db.rollback.assert_called_once_with(save_point="pulse_legacy_migration")
        self.frappe.db.commit.assert_not_called()
        self.assertEqual(self.flags, {"mute_emails": False, "in_import": "previous"})

    def test_database_aborted_transaction_does_not_mask_original_failure(self):
        original = RuntimeError("deadlock")
        self.stages[-1].side_effect = original
        self.frappe.db.rollback.side_effect = [RuntimeError("savepoint missing"), None]
        with self.assertRaisesRegex(RuntimeError, "deadlock") as raised:
            self.bridge.migrate(dry_run=False)
        self.assertIs(raised.exception, original)
        self.assertEqual(self.frappe.db.rollback.call_count, 2)
        self.frappe.db.rollback.assert_called_with()
        self.frappe.db.commit.assert_not_called()
        self.assertEqual(self.flags, {"mute_emails": False, "in_import": "previous"})

    def test_unresolved_reference_is_not_silently_dropped(self):
        self.frappe.db.exists.return_value = False
        with self.assertRaisesRegex(ValueError, "Unresolved legacy Task"):
            self.bridge._mapped("missing", {}, "Task")

    def test_mapping_wins_over_same_name_native_record(self):
        self.assertEqual(self.bridge._mapped("old", {"old": "new"}, "Task"), "new")
        self.frappe.db.exists.assert_not_called()

    def test_missing_schema_stops_before_transaction(self):
        self.frappe.db.has_column.return_value = False
        with self.assertRaisesRegex(ValueError, "bench migrate"):
            self.bridge.migrate()
        self.frappe.db.savepoint.assert_not_called()


if __name__ == "__main__":
    unittest.main()
