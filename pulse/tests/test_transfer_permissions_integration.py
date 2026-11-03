"""CSV permissions and retry/rollback guards against the real native backend."""
import csv
import io
from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import CallbackManager
from pulse.api import transfer


class TestTransferPermissions(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.mail_patch = patch('frappe.sendmail')
        self.mail_patch.start(); self.addCleanup(self.mail_patch.stop)
        suffix = frappe.generate_hash(length=8)
        self.user = 'csv-member-' + suffix + '@example.test'
        frappe.get_doc({'doctype': 'User', 'email': self.user, 'first_name': 'CSV Member',
            'user_type': 'System User', 'enabled': 1, 'send_welcome_email': 0,
            'roles': [{'role': 'Projects User'}]}).insert()
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Restricted CSV ' + suffix,
            'users': [{'user': self.user, 'welcome_email_sent': 1}]}).insert()
        self.content = 'subject,priority\nReadable export task,Low\nSecret export task,High\n'
        self.result = transfer.import_tasks(self.project.name, self.content)
        self.visible, self.hidden = self.result['created']
        frappe.get_doc({'doctype': 'User Permission', 'user': self.user, 'allow': 'Task',
            'for_value': self.visible, 'apply_to_all_doctypes': 0, 'applicable_for': 'Task'}).insert()
        frappe.clear_cache(user=self.user)

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_import_replay_does_not_return_hidden_task_ids(self):
        frappe.set_user(self.user)
        self.assertTrue(frappe.has_permission('Project', 'write', doc=self.project.name))
        self.assertTrue(frappe.has_permission('Task', 'write', doc=self.visible))
        self.assertFalse(frappe.has_permission('Task', 'write', doc=self.hidden))
        with self.assertRaises(frappe.PermissionError):
            transfer.import_tasks(self.project.name, self.content)
        frappe.set_user('Administrator')
        self.assertEqual(frappe.db.count('Task', {'project': self.project.name}), 2)
        self.assertEqual(frappe.db.count('Pulse Import Batch', {'project': self.project.name}), 1)

    def test_export_only_contains_native_readable_tasks(self):
        frappe.set_user(self.user)
        exported = transfer.export_tasks(self.project.name)
        rows = list(csv.DictReader(io.StringIO(exported['content'])))
        self.assertEqual(exported['count'], 1)
        self.assertEqual([row['name'] for row in rows], [self.visible])
        self.assertNotIn(self.hidden, exported['content'])
        self.assertNotIn('Secret export task', exported['content'])

    def test_task_move_after_preview_parse_is_rechecked_before_update(self):
        other = frappe.get_doc({'doctype': 'Project', 'project_name': 'Destination CSV ' + frappe.generate_hash(length=8)}).insert()
        original_parse = transfer._parse
        def parse_then_move(project, content):
            rows = original_parse(project, content)
            doc = frappe.get_doc('Task', self.visible)
            doc.project = other.name
            doc.save()
            return rows
        with patch.object(transfer, '_parse', side_effect=parse_then_move):
            with self.assertRaisesRegex(frappe.ValidationError, 'moved to another project'):
                transfer.import_tasks(self.project.name, f'name,subject\n{self.visible},Must not overwrite\n')
        doc = frappe.get_doc('Task', self.visible)
        self.assertEqual(doc.project, other.name)
        self.assertEqual(doc.subject, 'Readable export task')

    def test_failed_import_drops_commit_hooks_when_outer_caller_continues(self):
        staged_mail = Mock()
        original_get_doc = frappe.get_doc
        def get_doc_with_notification(*args, **kwargs):
            doc = original_get_doc(*args, **kwargs)
            if args and isinstance(args[0], dict) and args[0].get('doctype') == 'Task':
                original_insert = doc.insert
                def insert_with_callback(*insert_args, **insert_kwargs):
                    result = original_insert(*insert_args, **insert_kwargs)
                    frappe.db.after_commit.add(staged_mail)
                    return result
                doc.insert = insert_with_callback
            return doc
        with patch.object(frappe.db, 'after_commit', CallbackManager()):
            with patch.object(frappe, 'get_doc', side_effect=get_doc_with_notification):
                with self.assertRaises(frappe.ValidationError):
                    transfer.import_tasks(self.project.name, 'subject,expected_time\nStaged valid task,1\nInvalid task,-1\n')
            frappe.db.after_commit.run()
        staged_mail.assert_not_called()
        self.assertFalse(frappe.db.exists('Task', {'project': self.project.name, 'subject': 'Staged valid task'}))
        self.assertEqual(frappe.db.count('Pulse Import Batch', {'project': self.project.name}), 1)
