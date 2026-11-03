"""Reminder preference and current-state contracts without SMTP or a database."""
from contextlib import nullcontext
from datetime import date
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class Row(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


class TestReminderEmail(unittest.TestCase):
    def setUp(self):
        self.frappe = ModuleType('frappe')
        self.preferences = ModuleType('frappe.desk.doctype.notification_settings.notification_settings')
        self.preferences.is_email_enabled_for_feature = MagicMock(return_value=True)
        wrapper = ModuleType('frappe.desk.doctype.notification_settings'); wrapper.notification_settings = self.preferences
        utils = ModuleType('frappe.utils'); utils.getdate = lambda value: date.fromisoformat(str(value)[:10]); utils.get_url = lambda value='': 'https://qa.invalid' + value
        atomic = ModuleType('pulse.services.atomic'); atomic.atomic_scope = lambda label: nullcontext()
        model = ModuleType('frappe.model'); model.get_permitted_fields = MagicMock(return_value=['subject', 'exp_end_date'])
        self.model = model
        self.modules = {'frappe.model': model, 'frappe': self.frappe, 'frappe.utils': utils, 'pulse.services.atomic': atomic,
            'frappe.desk': ModuleType('frappe.desk'), 'frappe.desk.doctype': ModuleType('frappe.desk.doctype'),
            'frappe.desk.doctype.notification_settings': wrapper,
            'frappe.desk.doctype.notification_settings.notification_settings': self.preferences}
        self.patch = patch.dict(sys.modules, self.modules); self.patch.start(); self.addCleanup(self.patch.stop)
        spec = importlib.util.spec_from_file_location('reminder_email_under_test', Path(__file__).parents[1] / 'scheduled' / 'reminder_email.py')
        self.helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.helper)
        self.user = Row(name='reader@example.test', email='actual@example.test', enabled=1)
        self.task = Row(name='TASK-1', exp_end_date='2026-11-04', pulse_archived=0, status='Open', _assign='["reader@example.test"]')
        self.notice = Row(name='notice-1', recipient=self.user.name, reference_doctype='Task', reference_name=self.task.name,
            message='Due tomorrow: <Private task>', link_url='/pulse/board?task=TASK-1', email_queued=0)
        self.fields = {'subject': Row(mask=0), 'exp_end_date': Row(mask=0)}
        self.frappe.get_meta = MagicMock(return_value=Row(get_field=lambda name: self.fields.get(name)))
        self.frappe.get_cached_doc = MagicMock(return_value={'email_notifications': 1})
        self.frappe.get_doc = MagicMock(side_effect=lambda dt, name, **kw: {'User': self.user, 'Task': self.task, 'Pulse Notification': self.notice}[dt])
        self.frappe.db = MagicMock()
        self.pref = {'enabled': 1, 'enable_email_notifications': 1, 'enable_email_event_reminders': 1}
        self.frappe.db.get_value.side_effect = lambda dt, name, fields, **kw: Row(recipient=self.user.name, reference_doctype='Task', reference_name=self.task.name) if dt == 'Pulse Notification' else self.pref.get(fields)
        self.frappe.db.set_value.side_effect = lambda dt, name, field, value, **kw: setattr(self.notice, field, value)
        self.frappe.db.exists.return_value = True
        self.frappe.has_permission = MagicMock(return_value=True)
        self.frappe.parse_json = __import__('json').loads
        self.frappe.sendmail = MagicMock(return_value=Row(name='QUEUE-1'))
        self.frappe.log_error = MagicMock(); self.frappe.get_traceback = lambda: 'queue failure'
        self.frappe.throw = lambda message: (_ for _ in ()).throw(ValueError(message))

    def test_explicit_queue_is_once_escaped_and_uses_actual_user_email(self):
        self.assertTrue(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
        self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
        self.frappe.sendmail.assert_called_once()
        values = self.frappe.sendmail.call_args.kwargs
        self.assertEqual(values['recipients'], ['actual@example.test'])
        self.assertFalse(values['now']); self.assertTrue(values['delayed'])
        self.assertIn('&lt;Private task&gt;', values['message'])
        self.assertEqual(values['reference_name'], self.notice.name)
        self.assertEqual(self.notice.email_queued, 1)
        self.assertTrue(all(call.kwargs['for_update'] for call in self.frappe.get_doc.call_args_list))

    def test_queue_failure_or_empty_result_stays_retryable_and_logged(self):
        self.frappe.sendmail.side_effect = ValueError('No outgoing account')
        self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
        self.assertEqual(self.notice.email_queued, 0); self.frappe.log_error.assert_called_once()
        self.frappe.sendmail.side_effect = None; self.frappe.sendmail.return_value = None
        self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
        self.assertEqual(self.notice.email_queued, 0)
        self.frappe.sendmail.return_value = Row(name='QUEUE-1')
        self.assertTrue(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))

    def test_current_lifecycle_assignment_access_and_due_date_are_checked(self):
        cases = [(self.user, 'enabled', 0), (self.task, 'pulse_archived', 1), (self.task, 'status', 'Completed'),
                 (self.task, '_assign', '[]'), (self.task, 'exp_end_date', '2026-11-05')]
        for row, field, value in cases:
            old = getattr(row, field); setattr(row, field, value)
            self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
            setattr(row, field, old)
        self.frappe.has_permission.return_value = False
        self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
        self.frappe.sendmail.assert_not_called()

    def test_global_and_native_feature_preferences_are_respected(self):
        self.frappe.get_cached_doc.return_value = {'email_notifications': 0}
        self.assertFalse(self.helper.email_allowed(self.user.name))
        self.frappe.get_cached_doc.return_value = {'email_notifications': 1}
        self.pref['enabled'] = 0
        self.assertFalse(self.helper.email_allowed(self.user.name))
        self.pref['enabled'] = 1
        self.preferences.is_email_enabled_for_feature.return_value = False
        self.assertFalse(self.helper.email_allowed(self.user.name))
        self.preferences.is_email_enabled_for_feature.assert_called_with(self.user.name, 'enable_email_event_reminders')

    def test_older_frappe_fallback_reads_feature_not_notification_type_allowlist(self):
        del self.preferences.is_email_enabled_for_feature
        self.assertTrue(self.helper.email_allowed(self.user.name))
        for field in ('enable_email_notifications', 'enable_email_event_reminders'):
            self.pref[field] = 0; self.assertFalse(self.helper.email_allowed(self.user.name)); self.pref[field] = 1
        self.pref = {}; self.assertTrue(self.helper.email_allowed(self.user.name))

    def test_masked_or_fieldlevel_hidden_title_due_cannot_be_emailed(self):
        self.model.get_permitted_fields.return_value = ['subject']
        self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
        self.model.get_permitted_fields.return_value = ['subject', 'exp_end_date']
        for field in ('subject', 'exp_end_date'):
            self.fields[field].mask = 1
            self.assertFalse(self.helper.queue_reminder_email(self.notice.name, '2026-11-04'))
            self.fields[field].mask = 0
        self.frappe.sendmail.assert_not_called()
