"""Native assignment/offboarding serialization guards without a database."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
import sys


class TestOffboardingAssignmentGuard(TestCase):
    def setUp(self):
        self.frappe = SimpleNamespace(db=SimpleNamespace(get_value=Mock(return_value=1)),
            throw=Mock(side_effect=ValueError), _=lambda value: value,
            session=SimpleNamespace(user='Administrator'))
        spec = importlib.util.spec_from_file_location('team_assignment_guard',
            Path(__file__).parents[1] / 'hooks' / 'events' / 'assignment.py')
        self.module = importlib.util.module_from_spec(spec)
        self.modules = patch.dict(sys.modules, {'frappe': self.frappe,
            'pulse.services.hierarchy_service': SimpleNamespace(hierarchy_enabled=lambda: False, can_assign=Mock()),
            'pulse.hooks.permissions': SimpleNamespace(require_permission=Mock())})
        self.modules.start(); self.addCleanup(self.modules.stop)
        spec.loader.exec_module(self.module)

    def test_disabled_user_is_rejected_even_for_administrator_and_no_hierarchy(self):
        self.frappe.db.get_value.return_value = 0
        with self.assertRaises(ValueError):
            self.module.validate_assignment('Administrator', 'departing@example.test')
        self.frappe.db.get_value.assert_called_once_with('User', 'departing@example.test', 'enabled', for_update=True)

    def test_native_open_todo_uses_same_user_row_lock(self):
        fields = {'allocated_to': 'member@example.test', 'status': 'Open'}
        self.module.enforce_hierarchy(SimpleNamespace(doctype='ToDo', get=fields.get))
        self.frappe.db.get_value.assert_called_once_with('User', 'member@example.test', 'enabled', for_update=True)

    def test_closing_old_assignment_does_not_require_enabled_departing_user(self):
        self.frappe.db.get_value.return_value = 0
        fields = {'allocated_to': 'member@example.test', 'status': 'Closed'}
        self.module.enforce_hierarchy(SimpleNamespace(doctype='ToDo', get=fields.get))
        self.frappe.db.get_value.assert_not_called()
