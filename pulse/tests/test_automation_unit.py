import unittest
from unittest.mock import patch
import frappe
from pulse.api import automation, spa


class AutomationTests(unittest.TestCase):
    def test_create_uses_native_pulse_handler(self):
        with patch.object(spa, "create_task", return_value={"name": "TASK-1"}) as create:
            result = automation.execute("create_task", {"project": "PROJ-1", "subject": "Automated"})
        create.assert_called_once_with(project="PROJ-1", subject="Automated")
        self.assertEqual(result["name"], "TASK-1")

    def test_guest_cannot_dispatch(self):
        with patch.dict(frappe.session, {"user": "Guest"}), self.assertRaises(frappe.PermissionError):
            automation.execute("get_task", {"task": "TASK-1"})

    def test_rejects_arbitrary_operation_and_privileged_arguments(self):
        for operation, values in [("frappe.delete_doc", {}),
                ("create_task", {"project": "P", "subject": "T", "ignore_permissions": True})]:
            with self.assertRaises(frappe.ValidationError):
                automation.execute(operation, values)

    def test_status_uses_validating_workflow_handler(self):
        with patch.object(spa, "update_task_state", return_value={"ok": True}) as update:
            automation.execute("set_status", {"task": "TASK-1", "state": "Done"})
        update.assert_called_once_with(task="TASK-1", state="Done")
