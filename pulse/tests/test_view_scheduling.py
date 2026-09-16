"""Calendar multi-selection uses native validations in a single transaction."""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate
from pulse.api.views import schedule_tasks


class TestViewScheduling(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        from pulse.erpnext_bridge import ensure_default_company
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Schedule ' + frappe.generate_hash(length=8),
                                       'company': ensure_default_company()}).insert()
        self.tasks = [frappe.get_doc({'doctype': 'Task', 'subject': f'Schedule {i}', 'project': self.project.name,
                                     'exp_start_date': '2026-09-10', 'exp_end_date': '2026-09-12'}).insert() for i in range(2)]

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_schedules_multiple_tasks_preserving_duration(self):
        second = self.tasks[1]
        second.exp_start_date = None
        second.exp_end_date = None
        second.save()
        result = schedule_tasks([t.name for t in self.tasks], '2026-09-20')
        self.assertEqual(result['count'], 2)
        for task in self.tasks:
            task.reload()
            self.assertEqual(getdate(task.exp_end_date), getdate('2026-09-20'))
        self.assertEqual(getdate(self.tasks[0].exp_start_date), getdate('2026-09-18'))
        self.assertIsNone(self.tasks[1].exp_start_date)

    def test_later_native_validation_failure_rolls_back_first_task(self):
        frappe.db.set_value('Task', self.tasks[1].name, 'expected_time', -1)
        with self.assertRaises(frappe.ValidationError):
            schedule_tasks([t.name for t in self.tasks], '2026-09-20')
        self.assertEqual(getdate(frappe.db.get_value('Task', self.tasks[0].name, 'exp_end_date')), getdate('2026-09-12'))

    def test_checks_all_permissions_before_any_updates(self):
        user = 'calendar-' + frappe.generate_hash(length=8) + '@example.com'
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Calendar', 'send_welcome_email': 0,
                        'roles': [{'role': 'Pulse Senior Developer'}]}).insert()
        visible = frappe.get_doc({'doctype': 'Project', 'project_name': 'Visible ' + frappe.generate_hash(length=8),
                                  'company': self.project.company, 'users': [{'user': user, 'welcome_email_sent': 1}]}).insert()
        task = frappe.get_doc({'doctype': 'Task', 'subject': 'Visible task', 'project': visible.name,
                              'exp_end_date': '2026-09-12'}).insert()
        frappe.set_user(user)
        with self.assertRaises(frappe.PermissionError):
            schedule_tasks([task.name, self.tasks[0].name], '2026-09-20')
        self.assertEqual(getdate(frappe.db.get_value('Task', task.name, 'exp_end_date')), getdate('2026-09-12'))

    def test_rejects_invalid_date_and_excessive_selection(self):
        for tasks, date in [([], '2026-09-20'), ([self.tasks[0].name] * 201, '2026-09-20'), ([self.tasks[0].name], '2026-02-30')]:
            with self.assertRaises(frappe.ValidationError):
                schedule_tasks(tasks, date)

    def test_module_membership_and_schedule_succeed_together(self):
        from pulse.api.modules import save_module
        module = save_module(self.project.name, 'Calendar grouping')['name']
        result = schedule_tasks([task.name for task in self.tasks], '2026-09-20', module=module)
        self.assertEqual(result['count'], 2)
        for task in self.tasks:
            self.assertTrue(frappe.db.exists('Pulse Module Task', {'module': module, 'task': task.name}))
            self.assertEqual(getdate(frappe.db.get_value('Task', task.name, 'exp_end_date')), getdate('2026-09-20'))

    def test_module_links_roll_back_when_later_task_validation_fails(self):
        from pulse.api.modules import save_module
        module = save_module(self.project.name, 'Atomic calendar')['name']
        frappe.db.set_value('Task', self.tasks[1].name, 'expected_time', -1)
        with self.assertRaises(frappe.ValidationError):
            schedule_tasks([task.name for task in self.tasks], '2026-09-20', module=module)
        self.assertFalse(frappe.db.exists('Pulse Module Task', {'module': module}))
        self.assertEqual(getdate(frappe.db.get_value('Task', self.tasks[0].name, 'exp_end_date')), getdate('2026-09-12'))

    def test_cross_project_module_is_rejected_without_changing_dates(self):
        from pulse.api.modules import save_module
        other = frappe.get_doc({'doctype': 'Project', 'project_name': 'Other module ' + frappe.generate_hash(length=8),
                                'company': self.project.company}).insert()
        module = save_module(other.name, 'Other calendar')['name']
        with self.assertRaises(frappe.ValidationError):
            schedule_tasks([self.tasks[0].name], '2026-09-20', module=module)
        self.assertFalse(frappe.db.exists('Pulse Module Task', {'module': module}))
        self.assertEqual(getdate(frappe.db.get_value('Task', self.tasks[0].name, 'exp_end_date')), getdate('2026-09-12'))

    def test_assignable_users_are_project_members_and_project_requires_access(self):
        from pulse.api.spa import get_assignable_users
        emails = ['schedule-member-' + frappe.generate_hash(length=8) + '@example.com' for _ in range(2)]
        for email in emails:
            frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': 'Scheduler', 'send_welcome_email': 0,
                            'roles': [{'role': 'Pulse Senior Developer'}]}).insert()
        self.project.reload()
        self.project.append('users', {'user': emails[0], 'welcome_email_sent': 1})
        self.project.save()
        self.assertEqual([u.name for u in get_assignable_users(self.project.name)], [emails[0]])
        frappe.set_user(emails[1])
        with self.assertRaises(frappe.PermissionError):
            get_assignable_users(self.project.name)
