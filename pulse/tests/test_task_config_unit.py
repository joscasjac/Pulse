import importlib.util
import json
from datetime import date
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class Doc(dict):
    __getattr__ = dict.get
    def __setattr__(self, name, value):
        self[name] = value
    def get_doc_before_save(self):
        return self.get('_before')


class TaskConfigurationTests(unittest.TestCase):
    def setUp(self):
        def throw(message, *args):
            raise ValueError(message)
        self.project = Doc(pulse_task_statuses=[Doc(label="Queued", category="To Do", color="#123456"),
                                               Doc(label="Delivered", category="Done", color="#654321")],
                           pulse_task_types=[Doc(task_type="Bug")])
        self.frappe = SimpleNamespace(whitelist=lambda: lambda f: f, throw=throw, get_doc=Mock(return_value=self.project), db=SimpleNamespace(get_value=Mock(return_value="Other Project")))
        spec = importlib.util.spec_from_file_location('task_config_under_test', Path(__file__).parents[1] / 'api' / 'task_config.py')
        self.config = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': SimpleNamespace(getdate=lambda v: date.fromisoformat(str(v))),
                                      'pulse.hooks.permissions': SimpleNamespace(require_permission=Mock())}):
            spec.loader.exec_module(self.config)

    def task(self, **fields):
        return Doc(project="Project", type="Bug", status="Open", workflow_state="Queued", **fields)

    def test_custom_done_state_updates_native_status(self):
        task = self.task()
        task.workflow_state = "Delivered"
        self.config.validate_task(task)
        self.assertEqual(task.status, "Completed")

    def test_native_status_change_updates_custom_state(self):
        task = self.task(_before=Doc(project="Project", status="Open", workflow_state="Queued"))
        task.status = "Completed"
        self.config.validate_task(task)
        self.assertEqual(task.workflow_state, "Delivered")

    def test_unknown_state_rejected(self):
        task = self.task()
        task.workflow_state = "Other project status"
        with self.assertRaisesRegex(ValueError, 'configured'):
            self.config.validate_task(task)

    def test_estimates_must_be_finite_and_positive(self):
        for value in (-1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'nonnegative'):
                self.config.validate_task(self.task(expected_time=value))

    def test_dates_and_foreign_labels_rejected(self):
        with self.assertRaisesRegex(ValueError, 'start date'):
            self.config.validate_task(self.task(exp_start_date='2026-09-20', exp_end_date='2026-09-16'))
        with self.assertRaisesRegex(ValueError, 'same project'):
            self.config.validate_task(self.task(pulse_labels=[Doc(label='foreign')]))

    def test_disallowed_type_rejected(self):
        task = self.task()
        task.type = "Feature"
        with self.assertRaisesRegex(ValueError, 'task type'):
            self.config.validate_task(task)


if __name__ == '__main__':
    unittest.main()
