"""Native module scopes and membership transaction regressions."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys
import unittest


class ModulePermissionTests(unittest.TestCase):
    def setUp(self):
        self.frappe = SimpleNamespace(
            session=SimpleNamespace(user='member'), whitelist=lambda: lambda f: f,
            has_permission=Mock(return_value=True),
            get_list=Mock(side_effect=lambda dt, **kw: {'Project': ['project'], 'Task': ['visible-task'], 'Pulse Module': ['visible-module']}[dt]),
            db=SimpleNamespace(escape=lambda v: "'" + v + "'", savepoint=Mock(), rollback=Mock(), sql=Mock(), get_value=Mock(return_value=None)),
            generate_hash=Mock(return_value='test'),
        )
        self.require = Mock(return_value=SimpleNamespace(project='project'))
        self.scope = Mock(return_value=True)
        spec = importlib.util.spec_from_file_location('module_api_under_test', Path(__file__).parents[1] / 'api' / 'modules.py')
        self.api = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'pulse.hooks.permissions': SimpleNamespace(require_permission=self.require, scoped_has_permission=self.scope)}):
            spec.loader.exec_module(self.api)

    def test_membership_list_uses_native_task_and_module_visibility(self):
        sql = self.api.membership_query()
        self.assertIn("`module` IN ('visible-module')", sql)
        self.assertIn("`task` IN ('visible-task')", sql)
        self.assertEqual({c.args[0] for c in self.frappe.get_list.call_args_list}, {'Task', 'Pulse Module'})
        for call in self.frappe.get_list.call_args_list:
            self.assertEqual(call.kwargs['user'], 'member')

    def test_direct_membership_read_requires_module_access(self):
        self.frappe.has_permission.side_effect = lambda dt, *a, **kw: dt != 'Pulse Module'
        self.assertFalse(self.api.membership_permission(SimpleNamespace(module='hidden-module', task='visible-task'), debug=True, ptype='read'))
        self.scope.assert_called_once_with(unittest.mock.ANY, 'member', ptype='read', permission_type=None)

    def test_module_list_requires_native_project_visibility(self):
        self.assertEqual(self.api.query_conditions(), "`tabPulse Module`.`project` IN ('project')")
        self.frappe.has_permission.return_value = False
        self.assertIn('IN (NULL)', self.api.query_conditions())

    def test_late_membership_failure_rolls_back_earlier_insert(self):
        self.frappe.get_doc = Mock(side_effect=[SimpleNamespace(insert=Mock()), SimpleNamespace(insert=Mock(side_effect=RuntimeError('second row failed')))])
        with self.assertRaises(RuntimeError):
            self.api.set_tasks('module', ['first', 'second'])
        self.frappe.db.rollback.assert_called_once_with(save_point='pulse_module_test')

    def test_direct_membership_rejects_task_moved_after_snapshot(self):
        self.frappe.throw = Mock(side_effect=ValueError)
        self.frappe.db.get_value.return_value = 'new-project'
        spec = importlib.util.spec_from_file_location('membership_under_test', Path(__file__).parents[1] / 'pulse' / 'doctype' / 'pulse_module_task' / 'pulse_module_task.py')
        controller = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.model.document': SimpleNamespace(Document=object),
                                    'pulse.hooks.permissions': SimpleNamespace(require_permission=self.require)}):
            spec.loader.exec_module(controller)
        membership = controller.PulseModuleTask()
        membership.module = 'module'
        membership.task = 'task'
        with self.assertRaises(ValueError):
            membership.validate()
        self.frappe.db.get_value.assert_called_once_with('Task', 'task', 'project', for_update=True)
