"""Real reminder inboxes and Email Queue rows; SMTP is never contacted."""
import json
from email import message_from_string
import frappe
from unittest.mock import patch
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


class TestScheduledIntegration(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.smtp = patch('frappe.email.doctype.email_queue.email_queue.EmailQueue.send', side_effect=AssertionError('Scheduled tests must only queue email'))
        self.smtp.start(); self.addCleanup(self.smtp.stop)
        self.settings = frappe._dict(advance_reminders=1, reminder_days_before='1', email_notifications=1)
        original_cached = frappe.get_cached_doc
        self.cached = patch.object(frappe, 'get_cached_doc', side_effect=lambda dt, *a, **kw: self.settings if dt == 'Pulse Settings' else original_cached(dt, *a, **kw))
        self.cached.start(); self.addCleanup(self.cached.stop)
        suffix = frappe.generate_hash(length=8)
        self.user = 'reminder-' + suffix + '@example.test'
        frappe.get_doc({'doctype': 'User', 'email': self.user, 'first_name': 'Reminder Recipient',
            'user_type': 'System User', 'enabled': 1, 'send_welcome_email': 0,
            'roles': [{'role': 'Projects User'}]}).insert()
        prefs = frappe.get_doc('Notification Settings', self.user)
        prefs.enabled = 1; prefs.enable_email_notifications = 1; prefs.enable_email_event_reminders = 1
        prefs.save(ignore_permissions=True)
        self.account = frappe.get_doc({'doctype': 'Email Account', 'email_account_name': 'Pulse Reminder QA ' + suffix,
            'email_id': 'reminder-sender-' + suffix + '@example.test', 'enable_incoming': 0,
            'enable_outgoing': 1, 'default_outgoing': 1, 'no_smtp_authentication': 1,
            'smtp_server': '127.0.0.1', 'smtp_port': '1025', 'use_tls': 0}).insert()
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Scheduled email ' + suffix}).insert()
        frappe.db.set_value('Project', self.project.name, 'owner', self.user)
        self.task = self.make_task(add_days(today(), 1))
        # Keep scheduler enumeration fixture-scoped while exercising its real SQL filters.
        original_all = frappe.get_all
        def fixture_tasks(doctype, *args, **kwargs):
            if doctype == 'Task':
                filters = kwargs.get('filters') or {}
                kwargs['filters'] = {**filters, 'project': self.project.name} if isinstance(filters, dict) else [*filters, ['project', '=', self.project.name]]
            return original_all(doctype, *args, **kwargs)
        self.task_query = patch.object(frappe, 'get_all', side_effect=fixture_tasks)
        self.task_query.start(); self.addCleanup(self.task_query.stop)

    def tearDown(self):
        frappe.set_user('Administrator'); frappe.db.rollback()
        frappe.clear_cache(doctype='Email Account')
        frappe.clear_cache(doctype='Task')

    def make_task(self, due, archived=0):
        doc = frappe.get_doc({'doctype': 'Task', 'subject': 'Scheduled <reminder> acceptance',
            'project': self.project.name, 'exp_end_date': due, 'pulse_archived': archived}).insert()
        frappe.db.set_value('Task', doc.name, '_assign', json.dumps([self.user]))
        return doc

    def queues(self, task=None):
        notices = frappe.get_all('Pulse Notification', filters={'reference_name': (task or self.task).name}, pluck='name')
        return frappe.get_all('Email Queue', filters={'reference_doctype': 'Pulse Notification', 'reference_name': ['in', notices]}, fields=['name', 'status', 'message']) if notices else []

    def notice(self, task=None):
        return frappe.get_doc('Pulse Notification', {'reference_name': (task or self.task).name})

    def test_advance_reminders_queue_real_email_once_without_enabling_alert_email(self):
        from pulse.scheduled import reminders
        from frappe.desk.doctype.notification_settings import notification_settings as preferences
        type_gate = getattr(preferences, 'is_email_notifications_enabled_for_type', None)
        if callable(type_gate):
            self.assertFalse(type_gate(self.user, 'Alert'))
        # Older Frappe16 skips Alert directly in Notification Log; the real
        # exactly-one queue assertion below also catches any native duplicate.
        with patch.object(frappe, 'publish_realtime') as event:
            reminders.send_advance_reminders(); reminders.send_advance_reminders()
        self.assertEqual(sum((call.args[0] if call.args else call.kwargs.get('event')) == 'pulse_notification' for call in event.call_args_list), 1)
        queues = self.queues(); self.assertEqual(len(queues), 1)
        self.assertEqual(queues[0].status, 'Not Sent')
        self.assertIn('Due tomorrow', queues[0].message)
        self.assertIn(self.task.subject, queues[0].message)
        self.assertEqual(frappe.get_all('Email Queue Recipient', filters={'parent': queues[0].name}, pluck='recipient'), [self.user])
        self.assertEqual(self.notice().email_queued, 1)
        self.assertEqual(frappe.db.count('Notification Log', {'document_name': self.task.name}), 1)
        frappe.set_user(self.user)
        from pulse.api.personal import mark_read
        mark_read(self.notice().name)
        frappe.set_user('Administrator'); reminders.send_advance_reminders()
        self.assertEqual(self.notice().is_read, 1); self.assertEqual(len(self.queues()), 1)

    def test_queue_failure_rolls_back_attempt_keeps_inbox_and_retries(self):
        from pulse.scheduled import reminders
        original_send = frappe.sendmail
        def fail_after_queue(**values):
            original_send(**values)
            raise frappe.OutgoingEmailError('Injected failure after queue creation')
        with patch.object(frappe, 'sendmail', side_effect=fail_after_queue), patch.object(frappe, 'log_error') as log:
            reminders.send_advance_reminders()
        log.assert_called_once()
        self.assertEqual(self.notice().email_queued, 0)
        self.assertEqual(len(self.queues()), 0)
        reminders.send_advance_reminders(); reminders.send_advance_reminders()
        self.assertEqual(self.notice().email_queued, 1); self.assertEqual(len(self.queues()), 1)
        self.assertEqual(frappe.db.count('Pulse Notification', {'reference_name': self.task.name}), 1)

    def test_email_preferences_can_opt_out_then_opt_in_without_duplicate_inbox(self):
        from pulse.scheduled import reminders
        for field in ('enabled', 'enable_email_notifications', 'enable_email_event_reminders'):
            frappe.db.set_value('Notification Settings', self.user, field, 0)
            reminders.send_advance_reminders()
            self.assertEqual(len(self.queues()), 0)
            self.assertEqual(self.notice().email_queued, 0)
            frappe.db.set_value('Notification Settings', self.user, field, 1)
        self.settings.email_notifications = 0; reminders.send_advance_reminders()
        self.assertEqual(len(self.queues()), 0)
        self.settings.email_notifications = 1; reminders.send_advance_reminders()
        self.assertEqual(len(self.queues()), 1)
        self.assertEqual(frappe.db.count('Pulse Notification', {'reference_name': self.task.name}), 1)

    def test_no_access_and_disabled_recipient_are_not_notified(self):
        from pulse.scheduled import reminders
        frappe.db.set_value('Project', self.project.name, 'owner', 'Administrator')
        frappe.clear_document_cache('Project', self.project.name)
        reminders.send_advance_reminders()
        self.assertFalse(frappe.db.exists('Pulse Notification', {'reference_name': self.task.name}))
        frappe.db.set_value('Project', self.project.name, 'owner', self.user)
        frappe.db.set_value('User', self.user, 'enabled', 0)
        reminders.send_advance_reminders()
        self.assertEqual(len(self.queues()), 0)

    def test_retry_rechecks_current_due_assignment_and_completion(self):
        from pulse.scheduled import reminders
        from pulse.scheduled.reminder_email import queue_reminder_email
        self.settings.email_notifications = 0; reminders.send_advance_reminders()
        notice = self.notice(); self.settings.email_notifications = 1
        due = add_days(today(), 1)
        for field, value in (('exp_end_date', add_days(today(), 5)), ('_assign', '[]'), ('status', 'Completed'), ('pulse_archived', 1)):
            original = frappe.db.get_value('Task', self.task.name, field)
            frappe.db.set_value('Task', self.task.name, field, value)
            self.assertFalse(queue_reminder_email(notice.name, due))
            frappe.db.set_value('Task', self.task.name, field, original)
        self.assertEqual(len(self.queues()), 0)
        self.assertTrue(queue_reminder_email(notice.name, due)); self.assertEqual(len(self.queues()), 1)

    def digest_queues(self):
        notices = frappe.get_all('Pulse Notification', filters={'recipient': self.user,
            'name': ['like', 'pulse-overdue-digest-%']}, pluck='name')
        return frappe.get_all('Email Queue', filters={'reference_doctype': 'Pulse Notification',
            'reference_name': ['in', notices]}, fields=['name', 'message']) if notices else []

    def test_overdue_retries_are_once_per_day_and_exclude_archived(self):
        from pulse.scheduled.overdue import flag_overdue_tasks
        overdue = self.make_task(add_days(today(), -3))
        second = self.make_task(add_days(today(), -2))
        archived = self.make_task(add_days(today(), -3), archived=1)
        before_status = frappe.db.get_value('Task', overdue.name, 'status')
        flag_overdue_tasks(); flag_overdue_tasks()
        self.assertEqual(len(self.digest_queues()), 1)
        email = message_from_string(self.digest_queues()[0].message)
        html = next(part.get_payload(decode=True).decode('utf-8') for part in email.walk()
                    if part.get_content_type() == 'text/html')
        self.assertIn(overdue.name, html)
        self.assertIn(second.name, html)
        self.assertNotIn(archived.name, html)
        self.assertEqual(len(self.queues(archived)), 0)
        self.assertEqual(frappe.db.count('Pulse Notification', {'reference_name': overdue.name}), 1)
        frappe.set_user(self.user)
        from pulse.api.personal import mark_read
        mark_read(self.notice(overdue).name)
        frappe.set_user('Administrator'); flag_overdue_tasks()
        self.assertEqual(self.notice(overdue).is_read, 1)
        with patch('pulse.scheduled.overdue.today', return_value=add_days(today(), 1)):
            flag_overdue_tasks()
        self.assertEqual(len(self.digest_queues()), 2)
        self.assertEqual(frappe.db.get_value('Task', overdue.name, 'status'), before_status)

    def test_overdue_empty_and_all_completed_send_no_email(self):
        from pulse.scheduled.overdue import flag_overdue_tasks
        flag_overdue_tasks()
        self.assertEqual(self.digest_queues(), [])
        overdue = self.make_task(add_days(today(), -3))
        frappe.db.set_value('Task', overdue.name, 'status', 'Completed')
        flag_overdue_tasks()
        self.assertEqual(self.digest_queues(), [])

    def test_overdue_queue_failure_rolls_back_daily_marker_and_retries(self):
        from pulse.scheduled.overdue import flag_overdue_tasks
        from pulse.scheduled.overdue_digest import digest_name
        self.make_task(add_days(today(), -3))
        original_send = frappe.sendmail
        def fail_after_queue(**values):
            original_send(**values)
            raise frappe.OutgoingEmailError('Injected failure after queue creation')
        with patch.object(frappe, 'sendmail', side_effect=fail_after_queue), patch.object(frappe, 'log_error'):
            flag_overdue_tasks()
        self.assertFalse(frappe.db.exists('Pulse Notification', digest_name(self.user, today())))
        self.assertEqual(self.digest_queues(), [])
        flag_overdue_tasks(); flag_overdue_tasks()
        self.assertEqual(len(self.digest_queues()), 1)

    def test_overdue_identity_collision_cannot_queue_or_leave_renamed_marker(self):
        from pulse.scheduled.overdue import flag_overdue_tasks
        from pulse.scheduled.overdue_digest import digest_name, queue_overdue_digest
        overdue = self.make_task(add_days(today(), -3))
        flag_overdue_tasks()
        name = digest_name(self.user, today())
        before = frappe.db.count('Pulse Notification', {'recipient': self.user})
        get_value = frappe.db.get_value
        def stale_identity(dt, dn=None, fieldname='name', *args, **kwargs):
            if dt == 'Pulse Notification' and dn == name and kwargs.get('for_update'):
                return None
            return get_value(dt, dn, fieldname, *args, **kwargs)
        # Force the overlap's stale-read path through a real unique-key collision.
        # Frappe hash naming may insert a random fallback; the savepoint must undo it.
        with patch.object(frappe.db, 'get_value', side_effect=stale_identity), patch.object(frappe, 'sendmail') as send:
            self.assertFalse(queue_overdue_digest(self.user, [overdue.name], today()))
            send.assert_not_called()
        self.assertEqual(len(self.digest_queues()), 1)
        self.assertEqual(frappe.db.count('Pulse Notification', {'recipient': self.user}), before)

    def test_restricted_or_masked_title_due_are_not_written_to_any_inbox(self):
        from pulse.scheduled import reminders
        from frappe.model import get_permitted_fields
        from frappe.custom.doctype.property_setter.property_setter import make_property_setter
        setter = make_property_setter('Task', 'exp_end_date', 'permlevel', 1, 'Int')
        self.assertNotIn('exp_end_date', get_permitted_fields('Task', user=self.user, permission_type='read'))
        reminders.send_advance_reminders()
        self.assertFalse(frappe.db.exists('Pulse Notification', {'reference_name': self.task.name}))
        self.assertFalse(frappe.db.exists('Notification Log', {'document_name': self.task.name}))
        self.assertEqual(len(self.queues()), 0)
        frappe.delete_doc('Property Setter', setter.name, force=True)
        self.assertIn('exp_end_date', get_permitted_fields('Task', user=self.user, permission_type='read'))
        make_property_setter('Task', 'subject', 'mask', 1, 'Check')
        self.assertTrue(frappe.get_meta('Task').get_field('subject').get('mask'))
        reminders.send_advance_reminders()
        self.assertFalse(frappe.db.exists('Pulse Notification', {'reference_name': self.task.name}))
        self.assertEqual(len(self.queues()), 0)
