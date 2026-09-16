"""Saved-view ownership and preferences through the document/API boundary."""
import json
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api import views


class TestViews(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.users = []
        for _ in range(2):
            email = 'view-' + frappe.generate_hash(length=10) + '@example.com'
            frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': 'View tester',
                            'send_welcome_email': 0, 'roles': [{'role': 'Pulse Viewer'}]}).insert()
            self.users.append(email)

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_shared_view_is_read_only_for_other_user_and_private_view_is_hidden(self):
        frappe.set_user(self.users[0])
        private = views.save_view('Private', {})
        shared = views.save_view('Shared', {}, shared=1)
        frappe.set_user(self.users[1])
        names = {v.name for v in views.saved_views()}
        self.assertIn(shared['name'], names)
        self.assertNotIn(private['name'], names)
        self.assertFalse(frappe.has_permission('Pulse Saved View', 'read', doc=private['name']))
        with self.assertRaises(frappe.PermissionError):
            views.save_view('Stolen', {}, name=shared['name'])
        doc = frappe.get_doc('Pulse Saved View', shared['name'])
        doc.owner = self.users[1]
        with self.assertRaises(frappe.PermissionError):
            doc.save()

    def test_native_document_validation_and_private_preferences(self):
        frappe.set_user(self.users[0])
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({'doctype': 'Pulse Saved View', 'title': 'Malformed',
                            'configuration': json.dumps({'columns': []})}).insert()
        views.preferences({'layout': 'calendar', 'columns': ['subject']})
        frappe.set_user(self.users[1])
        self.assertEqual(views.preferences()['layout'], 'spreadsheet')
        frappe.set_user(self.users[0])
        self.assertEqual(views.preferences()['layout'], 'calendar')

    def test_workspace_preferences_are_isolated_by_user_project_and_editor(self):
        frappe.set_user(self.users[0])
        config = {'layout': 'timeline', 'filters': {'q': 'Client', 'priority': 'High'},
                  'include_archived': True, 'display_open': True}
        views.preferences(config, context='board:PROJECT-A')
        views.preferences({'layout': 'calendar', 'hide_weekends': False, 'order_by': 'modified', 'order_direction': 'desc', 'show_subtasks': False, 'calendar_layout': 'week'}, context='view:PROJECT-A')
        self.assertEqual(views.preferences(context='board:PROJECT-A')['layout'], 'timeline')
        self.assertEqual(views.preferences(context='board:PROJECT-A')['filters']['q'], 'Client')
        self.assertTrue(views.preferences(context='board:PROJECT-A')['include_archived'])
        self.assertEqual(views.preferences(context='board:PROJECT-B')['layout'], 'list')
        self.assertEqual(views.preferences(context='view:PROJECT-A')['layout'], 'calendar')
        self.assertFalse(views.preferences(context='view:PROJECT-A')['hide_weekends'])
        self.assertEqual(views.preferences(context='view:PROJECT-A')['order_by'], 'modified')
        self.assertEqual(views.preferences(context='view:PROJECT-A')['order_direction'], 'desc')
        self.assertFalse(views.preferences(context='view:PROJECT-A')['show_subtasks'])
        self.assertEqual(views.preferences(context='view:PROJECT-A')['calendar_layout'], 'week')
        self.assertTrue(views.preferences(context='view:PROJECT-B')['hide_weekends'])
        self.assertEqual(views.preferences()['layout'], 'spreadsheet')
        frappe.set_user(self.users[1])
        self.assertEqual(views.preferences(context='board:PROJECT-A')['layout'], 'list')
        with self.assertRaises(frappe.ValidationError):
            views.preferences({'layout': 'unknown'}, context='board:PROJECT-A')
        with self.assertRaises(frappe.ValidationError):
            views.preferences({'filters': {'q': []}}, context='board:PROJECT-A')
