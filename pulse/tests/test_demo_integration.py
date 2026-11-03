import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch
from pulse.demo import seed, TITLE, MARKER


class TestDemoDataset(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.previous = frappe.conf.get('pulse_demo_mode')

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.conf.pulse_demo_mode = self.previous
        frappe.db.rollback()

    def test_disabled_mode_changes_nothing(self):
        frappe.conf.pulse_demo_mode = 0
        before = frappe.db.count('Project')
        with self.assertRaises(frappe.ValidationError): seed()
        self.assertEqual(frappe.db.count('Project'), before)

    def test_repeat_seed_is_native_idempotent_and_sends_no_mail_or_users(self):
        frappe.conf.pulse_demo_mode = 1
        before_users = frappe.db.count('User')
        with patch('frappe.sendmail') as mail:
            first = seed(); second = seed()
            mail.assert_not_called()
        self.assertEqual(first, second)
        self.assertEqual(frappe.db.count('User'), before_users)
        self.assertEqual(frappe.db.get_value('Project', first['project'], 'notes'), MARKER)
        self.assertEqual(frappe.db.count('Task', {'project': first['project']}), 3)
        self.assertEqual(frappe.db.count('Pulse Module Task', {'module': first['module']}), 3)
        self.assertEqual(frappe.db.count('Task', {'project': first['project'], 'status': 'Completed'}), 1)

    def test_name_collision_refuses_to_adopt_existing_business_data(self):
        frappe.conf.pulse_demo_mode = 1
        frappe.get_doc({'doctype': 'Project', 'project_name': TITLE, 'notes': 'Real business project'}).insert()
        with self.assertRaises(frappe.ValidationError): seed()
        self.assertFalse(frappe.db.exists('Task', {'subject': 'Plan delivery'}))
