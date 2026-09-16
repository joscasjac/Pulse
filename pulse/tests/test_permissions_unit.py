"""Fast policy regressions; database/REST enforcement is covered by integration tests."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class PermissionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.frappe = SimpleNamespace(
            session=SimpleNamespace(user="junior@example.com"), local=SimpleNamespace(),
            get_roles=Mock(return_value=["Pulse Junior Developer"]),
            get_all=Mock(return_value=[]), parse_json=json.loads,
            db=SimpleNamespace(escape=lambda v: "'" + v.replace("'", "''") + "'", get_value=Mock(return_value="owner@example.com")),
        )
        spec = importlib.util.spec_from_file_location("permission_policy_under_test", Path(__file__).parents[1] / "hooks" / "permissions.py")
        self.policy = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec.loader.exec_module(self.policy)

    def task(self, **values):
        return SimpleNamespace(owner=values.get("owner", "owner@example.com"), get=lambda k: values.get(k))

    def test_zero_memberships_never_means_unrestricted(self):
        self.assertEqual(self.policy._allowed_projects("junior@example.com"), [])
        self.assertIs(self.policy.task_has_permission(self.task(project="secret")), False)
        self.assertIn("tabProject User", self.policy.task_query_conditions())

    def test_project_member_junior_must_be_exact_assignee_or_owner(self):
        self.frappe.get_all.return_value = ["shared"]
        self.assertIs(self.policy.task_has_permission(self.task(project="shared", _assign='["other-junior@example.com"]')), False)
        self.assertIs(self.policy.task_has_permission(self.task(project="shared", _assign='["junior@example.com"]')), True)
        self.assertIn("JSON_CONTAINS", self.policy.task_query_conditions())

    def test_assignment_does_not_bypass_project_membership(self):
        self.assertIs(self.policy.task_has_permission(self.task(project="secret", _assign='["junior@example.com"]')), False)

    def test_new_task_assignment_checks_hierarchy_without_previous_document(self):
        validate = Mock(side_effect=PermissionError)
        doc = self.task(_assign='["manager@example.com"]')
        doc.get_doc_before_save = lambda: None
        with patch.dict(sys.modules, {"pulse.hooks.events.assignment": SimpleNamespace(validate_assignment=validate)}):
            with self.assertRaises(PermissionError):
                self.policy.validate_task_assignees(doc)
        validate.assert_called_once_with("junior@example.com", "manager@example.com")

    def test_admin_policy_defers_to_native_permissions(self):
        self.assertEqual(self.policy.task_query_conditions("Administrator"), "")
        self.assertIs(self.policy.task_has_permission(self.task(project="secret"), user="Administrator"), True)

    def test_checked_document_does_not_return_after_denial(self):
        doc = Mock()
        doc.check_permission.side_effect = PermissionError
        self.frappe.get_doc = Mock(return_value=doc)
        with self.assertRaises(PermissionError):
            self.policy.require_permission("Task", "secret", "write")
        doc.check_permission.assert_called_once_with("write")

    def test_timesheet_user_cannot_read_other_users_time(self):
        self.assertIs(self.policy.timesheet_has_permission(self.task(user="another@example.com")), False)
        self.assertIs(self.policy.timesheet_has_permission(self.task(user="junior@example.com")), True)

    def test_dependency_requires_both_endpoints(self):
        self.frappe.has_permission = Mock(side_effect=lambda dt, perm, doc, user: doc != "hidden")
        dependency = self.task(source_task="visible", target_task="hidden")
        dependency.doctype = "Pulse Dependency"
        self.assertIs(self.policy.scoped_has_permission(dependency), False)
        self.frappe.get_list = Mock(return_value=["visible"])
        query = self.policy.scoped_query_conditions(doctype="Pulse Dependency")
        self.assertIn("`source_task` IN ('visible')", query)
        self.assertIn("`target_task` IN ('visible')", query)
        self.frappe.get_list.assert_called_once_with("Task", pluck="name", limit_page_length=0, user="junior@example.com")

    def test_legacy_time_checks_owner_and_every_linked_row(self):
        self.frappe.has_permission = Mock(return_value=False)
        row = {"task": "hidden", "project": "secret"}
        self.assertIs(self.policy.timesheet_has_permission(self.task(user="junior@example.com", entries=[row])), False)
        self.frappe.get_list = Mock(side_effect=[["visible"], ["shared"]])
        query = self.policy.legacy_timesheet_query_conditions()
        self.assertIn("`tabPulse Timesheet Entry`", query)
        self.assertIn("td.task NOT IN ('visible')", query)
        self.assertIn("`tabPulse Timesheet`.`user` = 'junior@example.com'", query)

    def test_todo_uses_session_identity_and_checks_parent_write(self):
        hierarchy = SimpleNamespace(can_assign=Mock(return_value=False), hierarchy_enabled=lambda: True)
        self.frappe._ = lambda value: value
        self.frappe.bold = lambda value: value
        self.frappe.throw = Mock(side_effect=PermissionError)
        checked = Mock()
        spec = importlib.util.spec_from_file_location("assignment_under_test", Path(__file__).parents[1] / "hooks" / "events" / "assignment.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"frappe": self.frappe, "pulse.services.hierarchy_service": hierarchy,
                                     "pulse.hooks.permissions": SimpleNamespace(require_permission=checked)}):
            spec.loader.exec_module(module)
            todo = self.task(reference_type="Task", reference_name="hidden", allocated_to="boss", assigned_by="Administrator")
            todo.doctype = "ToDo"
            todo.reference_name = "hidden"
            with self.assertRaises(PermissionError):
                module.enforce_hierarchy(todo)
        checked.assert_called_once_with("Task", "hidden", "write")
        hierarchy.can_assign.assert_called_once_with("junior@example.com", "boss")

    def test_private_attachment_checks_old_and_new_parent_and_rejects_public(self):
        self.frappe.PermissionError = PermissionError
        self.frappe.throw = Mock(side_effect=PermissionError)
        checked = Mock()
        before = {"attached_to_doctype": "Task", "attached_to_name": "original"}
        file = self.task(attached_to_doctype="Pulse Document", attached_to_name="destination", is_private=0, file_url="/files/test.txt")
        file.get_doc_before_save = lambda: before
        with patch.object(self.policy, "require_permission", checked), self.assertRaises(PermissionError):
            self.policy.validate_private_attachment(file)
        self.assertEqual({call.args for call in checked.call_args_list}, {("Task", "original", "write"), ("Pulse Document", "destination", "write")})

    def test_revoked_attachment_owner_is_denied_by_parent_scope(self):
        self.frappe.has_permission = Mock(return_value=False)
        file = self.task(owner="junior@example.com", attached_to_doctype="Task", attached_to_name="revoked")
        self.assertIs(self.policy.attachment_has_permission(file, permission_type="read"), False)
        self.frappe.has_permission.assert_called_once_with("Task", "read", doc="revoked", user="junior@example.com")

    def test_native_download_checks_parent_before_owner_shortcut(self):
        class NativeFile:
            def is_downloadable(self):
                return True  # Native File permits its owner even after parent revocation.

        class ProtectedFile(self.policy.PrivateAttachmentDownloadMixin, NativeFile):
            def get(self, key):
                return {"attached_to_doctype": "Task", "attached_to_name": "revoked"}.get(key)

        self.frappe.has_permission = Mock(return_value=False)
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            self.assertFalse(ProtectedFile().is_downloadable())
        self.frappe.has_permission.return_value = True
        self.assertTrue(ProtectedFile().is_downloadable())

    def test_unrelated_native_file_download_behavior_is_preserved(self):
        class NativeFile:
            def is_downloadable(self):
                return "native result"

        class UnrelatedFile(self.policy.PrivateAttachmentDownloadMixin, NativeFile):
            def get(self, key):
                return {"attached_to_doctype": "Sales Invoice", "attached_to_name": "invoice"}.get(key)

        self.assertEqual(UnrelatedFile().is_downloadable(), "native result")


if __name__ == "__main__":
    unittest.main()
