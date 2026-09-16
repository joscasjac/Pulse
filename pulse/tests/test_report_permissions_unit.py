"""Report permission regressions without a database."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys
import unittest


class ReportPermissionTests(unittest.TestCase):
    def load(self, report, frappe, permission, extra=None):
        modules = {"frappe": frappe, "frappe.utils": SimpleNamespace(getdate=lambda d: d, add_days=Mock()),
                   "pulse.hooks.permissions": SimpleNamespace(require_permission=permission)}
        modules.update(extra or {})
        name = "pulse_" + report
        spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "pulse" / "report" / name / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)
        return module, modules

    def test_cycle_and_lead_sql_only_receive_visible_native_task_ids(self):
        for report in ("cycle_time", "lead_time"):
            with self.subTest(report=report):
                frappe = SimpleNamespace(_=lambda v: v, get_list=Mock(return_value=["visible"]), db=SimpleNamespace(sql=Mock(return_value=[])))
                permission = Mock()
                module, modules = self.load(report, frappe, permission)
                module.get_holiday_list = Mock(return_value=None)
                with patch.dict(sys.modules, modules):
                    module.execute({"project": "allowed"})
                permission.assert_called_once_with("Project", "allowed")
                sql, values = frappe.db.sql.call_args.args
                self.assertIn("`tabTask`", sql)
                self.assertNotIn("`tabPulse Task`", sql)
                self.assertIn("t.name IN %(visible)s", sql)
                self.assertEqual(values["visible"], ("visible",))
                frappe.get_list.return_value = []
                frappe.db.sql.reset_mock()
                with patch.dict(sys.modules, modules):
                    self.assertEqual(module.execute({"project": "allowed"}), ([], []))
                frappe.db.sql.assert_not_called()

    def test_cumulative_logs_use_visible_task_set(self):
        frappe = SimpleNamespace(_=lambda v: v, get_list=Mock(side_effect=[["visible"], []]))
        permission = Mock()
        module, modules = self.load("cumulative_flow", frappe, permission)
        with patch.dict(sys.modules, modules):
            self.assertEqual(module.execute({"project": "allowed"}), ([], []))
        log_call = frappe.get_list.call_args
        self.assertEqual(log_call.args[0], "Pulse Task Status Log")
        self.assertEqual(log_call.kwargs["filters"]["task"], ["in", ["visible"]])

    def test_velocity_does_not_bypass_frozen_outcome_permissions(self):
        sprint = SimpleNamespace(name="sprint", start_date="2026-09-01", end_date="2026-09-14")
        frappe = SimpleNamespace(get_list=Mock(return_value=[sprint]))
        permission = Mock(return_value={"closure_summary": "recorded"})
        progress = Mock(side_effect=PermissionError)
        module, modules = self.load("velocity", frappe, permission, {"pulse.api.planning": SimpleNamespace(sprint_progress=progress)})
        with patch.dict(sys.modules, modules), self.assertRaises(PermissionError):
            module.execute({"project": "allowed"})
        progress.assert_called_once_with("sprint")
