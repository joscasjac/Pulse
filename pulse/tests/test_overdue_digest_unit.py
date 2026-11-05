"""Daily digest contracts with no database, network, or real email."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
from pulse.tests import test_reminder_email_unit as reminder_tests

Row = reminder_tests.Row


class TestOverdueDigest(unittest.TestCase):
    def setUp(self):
        reminder_tests.TestReminderEmail.setUp(self)
        self.frappe._ = lambda text: text
        self.frappe.DoesNotExistError = type('DoesNotExistError', (Exception,), {})
        self.frappe.DuplicateEntryError = type('DuplicateEntryError', (Exception,), {})
        self.frappe.publish_realtime = MagicMock()
        self.users = {self.user.name: self.user}
        self.task.subject = '<Private task> & review'
        self.tasks = {self.task.name: self.task}
        self.notices = {}
        self.queues = []

        @contextmanager
        def transaction(label):
            notices, queues = deepcopy(self.notices), list(self.queues)
            try:
                yield
            except BaseException:
                self.notices, self.queues = notices, queues
                raise
        self.modules['pulse.services.atomic'].atomic_scope = transaction
        self.frappe.get_doc.side_effect = self.get_doc
        preference_value = self.frappe.db.get_value.side_effect
        self.frappe.db.get_value.side_effect = lambda dt, name, field, **kw: (name if name in self.notices else None) if dt == 'Pulse Notification' else preference_value(dt, name, field, **kw)
        self.frappe.db.exists.side_effect = lambda dt, name: name in (self.notices if dt == 'Pulse Notification' else self.queues)
        self.frappe.db.set_value.side_effect = lambda dt, name, field, value, **kw: setattr(self.notices[name], field, value)
        def send(**kwargs):
            name = 'QUEUE-' + str(len(self.queues))
            self.queues.append(name)
            return Row(name=name)
        self.frappe.sendmail.side_effect = send
        spec = importlib.util.spec_from_file_location('overdue_digest_under_test', Path(__file__).parents[1] / 'scheduled' / 'overdue_digest.py')
        self.digest = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'pulse.scheduled.reminder_email': self.helper}):
            spec.loader.exec_module(self.digest)

    def get_doc(self, dt, name=None, **kwargs):
        if isinstance(dt, dict):
            notice = Row(**dt)
            def insert(**kw):
                name = kw['set_name']
                if name in self.notices:
                    raise self.frappe.DuplicateEntryError()
                notice.name = name
                self.notices[name] = notice
                return notice
            notice.insert = insert
            return notice
        rows = {'User': self.users, 'Task': self.tasks, 'Pulse Notification': self.notices}[dt]
        if name not in rows:
            raise self.frappe.DoesNotExistError()
        return rows[name]

    def run_digest(self, names=None, day='2026-11-05'):
        return self.digest.queue_overdue_digest(self.user.name, list(self.tasks) if names is None else names, day)

    def test_81_tasks_for_two_users_produce_two_separate_emails(self):
        other = Row(name='other@example.test', email='other-delivery@example.test', enabled=1)
        self.users[other.name] = other
        self.tasks = {}
        for i in range(81):
            user = self.user if i < 59 else other
            self.tasks[str(i)] = Row(name=str(i), subject=f'Unique task {i}', exp_end_date='2026-11-04',
                status='Open', pulse_archived=0, _assign=json.dumps([user.name]))
        for user in self.users:
            self.assertTrue(self.digest.queue_overdue_digest(user, list(self.tasks), '2026-11-05'))
            self.assertFalse(self.digest.queue_overdue_digest(user, list(self.tasks), '2026-11-05'))
        calls = self.frappe.sendmail.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs['message'].count('<li>'), 59)
        self.assertEqual(calls[1].kwargs['message'].count('<li>'), 22)
        self.assertNotIn('Unique task 59<', calls[0].kwargs['message'])
        self.assertNotIn('Unique task 0<', calls[1].kwargs['message'])
        self.assertEqual(calls[1].kwargs['recipients'], [other.email])

    def test_daily_identity_escaping_and_native_queue_retry(self):
        self.assertTrue(self.run_digest(['TASK-1', 'TASK-1']))
        self.task.exp_end_date = '2026-11-03'
        self.assertFalse(self.run_digest())
        self.assertTrue(self.run_digest(day='2026-11-06'))
        self.assertEqual(len(self.queues), 2)
        payload = self.frappe.sendmail.call_args.kwargs
        self.assertIn('&lt;Private task&gt; &amp; review', payload['message'])
        self.assertEqual(payload['message'].count('<li>'), 1)
        self.assertIn('/pulse/board?task=TASK-1', payload['message'])
        self.assertFalse(payload['now']); self.assertTrue(payload['delayed'])
        self.assertTrue(all(n.email_queued == 1 for n in self.notices.values()))
        self.assertTrue(all(c.kwargs['for_update'] for c in self.frappe.get_doc.call_args_list if isinstance(c.args[0], str)))

    def test_current_state_empty_missing_and_permissions(self):
        for field, value in [('status', 'Completed'), ('status', 'Cancelled'), ('pulse_archived', 1),
                             ('exp_end_date', None), ('exp_end_date', '2026-11-05'), ('exp_end_date', '2026-11-06'),
                             ('_assign', '[]'), ('_assign', 'invalid'), ('_assign', '{}')]:
            old = getattr(self.task, field)
            setattr(self.task, field, value)
            self.assertFalse(self.run_digest(), (field, value))
            setattr(self.task, field, old)
        self.assertFalse(self.run_digest([]))
        self.assertFalse(self.run_digest(['DELETED']))
        self.frappe.has_permission.return_value = False
        self.assertFalse(self.run_digest())
        self.frappe.has_permission.return_value = True
        self.fields['subject'].mask = 1
        self.assertFalse(self.run_digest())
        self.frappe.sendmail.assert_not_called()
        self.assertEqual(self.notices, {})

    def test_disabled_preferences_users_and_missing_email(self):
        for field, value in [('enabled', 0), ('email', None)]:
            old = getattr(self.user, field); setattr(self.user, field, value)
            self.assertFalse(self.run_digest()); setattr(self.user, field, old)
        self.frappe.get_cached_doc.return_value = {'email_notifications': 0}
        self.assertFalse(self.run_digest())
        self.frappe.get_cached_doc.return_value = {'email_notifications': 1}
        self.preferences.is_email_enabled_for_feature.return_value = False
        self.assertFalse(self.run_digest())
        self.frappe.sendmail.assert_not_called()

    def test_failure_after_queue_rolls_back_marker_and_queue_then_retries(self):
        original = self.frappe.sendmail.side_effect
        def fail(**kw):
            original(**kw)
            raise RuntimeError('injected failure after insert')
        self.frappe.sendmail.side_effect = fail
        self.assertFalse(self.run_digest())
        self.assertEqual(self.notices, {}); self.assertEqual(self.queues, [])
        self.frappe.sendmail.side_effect = original
        self.assertTrue(self.run_digest()); self.assertFalse(self.run_digest())
        self.assertEqual(len(self.queues), 1)

    def test_unique_identity_prevents_queue_when_overlapping_snapshot_is_stale(self):
        self.assertTrue(self.run_digest())
        original = self.frappe.db.exists.side_effect
        preference_value = self.frappe.db.get_value.side_effect
        self.frappe.db.get_value.side_effect = lambda dt, name, field, **kw: (name if name in self.notices else None) if dt == 'Pulse Notification' else preference_value(dt, name, field, **kw)
        self.frappe.db.exists.side_effect = lambda dt, name: False if dt == 'Pulse Notification' else original(dt, name)
        self.assertFalse(self.run_digest())
        self.frappe.sendmail.assert_called_once()

    def test_frappe_hash_collision_renaming_rolls_back_before_queueing(self):
        original = self.frappe.get_doc.side_effect
        def get_doc(dt, name=None, **kwargs):
            doc = original(dt, name, **kwargs)
            if isinstance(dt, dict):
                insert = doc.insert
                def renamed(**kw):
                    kw['set_name'] = 'random-hash-fallback'
                    return insert(**kw)
                doc.insert = renamed
            return doc
        self.frappe.get_doc.side_effect = get_doc
        self.assertFalse(self.run_digest())
        self.assertEqual(self.notices, {})
        self.frappe.sendmail.assert_not_called()

    def test_all_previously_overdue_tasks_completed_means_no_next_day_email(self):
        self.assertTrue(self.run_digest())
        self.task.status = 'Completed'
        self.assertFalse(self.run_digest(day='2026-11-06'))
        self.assertEqual(len(self.queues), 1)
        self.assertNotIn(self.digest.digest_name(self.user.name, '2026-11-06'), self.notices)

    def test_missing_queue_row_rolls_back_marker(self):
        self.frappe.sendmail.side_effect = None
        self.frappe.sendmail.return_value = None
        self.assertFalse(self.run_digest())
        self.assertEqual(self.notices, {})
