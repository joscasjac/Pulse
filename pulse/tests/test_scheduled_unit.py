"""Scheduled notification regression tests without a database dependency."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class ScheduledTests(unittest.TestCase):
    def load_job(self, name):
        frappe = types.ModuleType("frappe")
        utils = types.ModuleType("frappe.utils")
        utils.today = lambda: "2026-09-16"
        utils.getdate = lambda value: value
        frappe.get_all = MagicMock()
        frappe.parse_json = json.loads
        frappe.db = MagicMock()
        frappe.has_permission = MagicMock()
        frappe.get_doc = MagicMock()
        frappe._ = lambda value: value
        path = Path(__file__).parents[1] / "scheduled" / (name + ".py")
        spec = importlib.util.spec_from_file_location("scheduled_under_test", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils}):
            spec.loader.exec_module(module)
        return module, frappe

    def test_overdue_native_tasks_only_notify_enabled_authorized_assignees(self):
        job, frappe = self.load_job("overdue")
        frappe.get_all.return_value = [types.SimpleNamespace(name="TASK-1", subject="Private task",
            _assign=json.dumps(["member", "member", "removed", "disabled", "Guest"]))]
        frappe.db.get_value.side_effect = lambda dt, user, field: user != "disabled"
        frappe.has_permission.side_effect = lambda dt, perm, doc, user: user == "member"
        job.flag_overdue_tasks()
        query = frappe.get_all.call_args
        self.assertEqual(query.args, ("Task",))
        self.assertEqual(query.kwargs["filters"]["pulse_archived"], 0)
        self.assertEqual(query.kwargs["filters"]["status"], ["not in", ("Completed", "Cancelled")])
        self.assertEqual(frappe.get_doc.call_count, 1)
        notification = frappe.get_doc.call_args.args[0]
        self.assertEqual(notification["document_type"], "Task")
        self.assertEqual(notification["for_user"], "member")
        frappe.get_doc.return_value.insert.assert_called_once_with(ignore_permissions=True)
        frappe.db.bulk_insert.assert_not_called()

    def test_bad_assignment_metadata_does_not_abort_other_tasks(self):
        job, frappe = self.load_job("overdue")
        frappe.get_all.return_value = [types.SimpleNamespace(name="TASK-1", subject="Task", _assign=value)
                                      for value in ('{"user":"member"}', 'invalid', 'null', '[]')]
        job.flag_overdue_tasks()
        frappe.get_doc.assert_not_called()

    def test_metrics_exclude_archived_and_use_native_completion(self):
        job, frappe = self.load_job("metrics")
        frappe.get_all.side_effect = [["SPRINT-1"], [
            types.SimpleNamespace(pulse_sprint="SPRINT-1", status="Open", workflow_state="Done"),
            types.SimpleNamespace(pulse_sprint="SPRINT-1", status="Completed", workflow_state="Delivered"),
        ]]
        job.snapshot_burndown()
        self.assertEqual(frappe.get_all.call_args.kwargs["filters"]["pulse_archived"], 0)
        frappe.get_doc.return_value.db_set.assert_any_call("planned_tasks", 2, update_modified=False)
        frappe.get_doc.return_value.db_set.assert_any_call("completed_tasks", 1, update_modified=False)

    def test_recurring_respects_renamed_project_status(self):
        job, frappe = self.load_job("recurring")
        config = types.ModuleType("pulse.api.task_config")
        config.CATEGORY_STATUS = {"To Do": "Open"}
        config.statuses_for = lambda project: [{"label": "Ready for work", "category": "To Do"}]
        template = types.SimpleNamespace(subject="Repeat", project="PROJECT-1", task_type=None,
            priority="Medium", description="", name="RECUR-1", next_run="2026-09-16", assign_to=None)
        with patch.dict(sys.modules, {"pulse.api.task_config": config}):
            job._spawn_task(template)
        values = frappe.get_doc.call_args.args[0]
        self.assertEqual(values["doctype"], "Task")
        self.assertEqual(values["workflow_state"], "Ready for work")
        self.assertEqual(values["status"], "Open")
