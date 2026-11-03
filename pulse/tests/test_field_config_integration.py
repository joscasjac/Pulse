import frappe
from frappe.tests import IntegrationTestCase
from pulse.api import task_config


class TestFieldConfiguration(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Fields ' + frappe.generate_hash(length=8)}).insert()
        self.task = frappe.get_doc({'doctype': 'Task', 'subject': 'Field acceptance', 'project': self.project.name}).insert()

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_required_fields_enforced_on_native_save_and_api(self):
        task_config.save_field_config(self.project.name, [{'fieldname': 'exp_end_date', 'show_in_form': 1, 'required_statuses': 'Done'}])
        self.task.workflow_state = 'Done'
        with self.assertRaises(frappe.ValidationError):
            self.task.save()
        from pulse.api.tasks import bulk_update
        with self.assertRaises(frappe.ValidationError):
            bulk_update([self.task.name], {'workflow_state': 'Done'})
        task_config.update_task_fields(self.task.name, {'exp_end_date': '2026-11-10'})
        self.task.reload(); self.task.workflow_state = 'Done'; self.task.save()
        self.assertEqual(self.task.status, 'Completed')

    def test_rejects_unknown_status_and_privileged_fields(self):
        for rule in ({'fieldname': 'owner', 'required_statuses': ''}, {'fieldname': 'priority', 'required_statuses': 'Imaginary'}):
            with self.assertRaises(frappe.ValidationError):
                task_config.save_field_config(self.project.name, [rule])
        task_config.save_field_config(self.project.name, [{'fieldname': 'priority', 'show_in_form': 1}])
        with self.assertRaises(frappe.ValidationError):
            task_config.update_task_fields(self.task.name, {'owner': 'Guest'})
        with self.assertRaises(frappe.ValidationError):
            task_config.update_task_fields(self.task.name, {'subject': 'Unconfigured'})

    def test_optional_zero_is_present_and_hidden_form_fields_are_not_returned(self):
        task_config.save_field_config(self.project.name, [{'fieldname': 'expected_time', 'show_in_form': 0, 'required_statuses': 'Done'}, {'fieldname': 'priority', 'show_in_form': 1}])
        self.task.expected_time = 0; self.task.workflow_state = 'Done'; self.task.save()
        data = task_config.get_task_fields(self.task.name)
        self.assertEqual([field['fieldname'] for field in data['fields']], ['priority'])
        self.assertNotIn('expected_time', data['values'])

    def test_member_cannot_change_required_rules_through_native_project_save(self):
        email = 'field-member-' + frappe.generate_hash(length=8) + '@example.test'
        frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': 'Fields', 'send_welcome_email': 0,
            'roles': [{'role': 'Projects Manager'}]}).insert()
        # Own project ensures row scope is readable/writable without invitation email.
        self.project.owner = email
        frappe.db.set_value('Project', self.project.name, 'owner', email)
        frappe.set_user(email)
        project = frappe.get_doc('Project', self.project.name)
        project.append('pulse_task_field_rules', {'fieldname': 'priority', 'required_statuses': 'Done'})
        with self.assertRaises(frappe.PermissionError):
            project.save()
        with self.assertRaises(frappe.PermissionError):
            task_config.create_custom_task_field(self.project.name, 'Restricted company field')

    def test_hidden_project_denied(self):
        frappe.set_user('Guest')
        for action in (lambda: task_config.get_field_config(self.project.name), lambda: task_config.get_task_fields(self.task.name),
                       lambda: task_config.save_field_config(self.project.name, [])):
            with self.assertRaises(frappe.PermissionError):
                action()


class TestNativeCustomField(IntegrationTestCase):
    def test_company_select_field_created_configured_and_enforced(self):
        frappe.set_user('Administrator')
        project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Custom fields ' + frappe.generate_hash(length=8)}).insert()
        task = None
        custom = None
        reader = None
        try:
            result = task_config.create_custom_task_field(project.name, 'QA field ' + frappe.generate_hash(length=8), 'Select', 'Review\nReady')
            fieldname = result['fieldname']; custom = 'Task-' + fieldname
            self.assertTrue(frappe.db.exists('Custom Field', custom))
            task_config.save_field_config(project.name, [{'fieldname': fieldname, 'show_in_form': 1, 'required_statuses': 'Done'}])
            task = frappe.get_doc({'doctype': 'Task', 'subject': 'Native custom value', 'project': project.name}).insert()
            task_config.update_task_fields(task.name, {fieldname: 'Ready'})
            task.reload(); self.assertEqual(task.get(fieldname), 'Ready')
            task.workflow_state = 'Done'; task.save()
            task.set(fieldname, '')
            with self.assertRaises(frappe.ValidationError):
                task.save()
            with self.assertRaises(frappe.ValidationError):
                task_config.create_custom_task_field(project.name, 'Not allowed', 'Link', 'User')
            reader = 'field-read-' + frappe.generate_hash(length=8) + '@example.test'
            frappe.get_doc({'doctype': 'User', 'email': reader, 'first_name': 'Field reader', 'send_welcome_email': 0,
                'roles': [{'role': 'Projects User'}]}).insert()
            restricted = frappe.get_doc('Custom Field', custom); restricted.permlevel = 1; restricted.save()
            frappe.db.set_value('Project', project.name, 'owner', reader)
            frappe.clear_document_cache('Project', project.name)
            frappe.set_user(reader)
            self.assertNotIn(fieldname, task_config.get_task_fields(task.name)['values'])
            self.assertNotIn(fieldname, [field['fieldname'] for field in task_config.get_field_config(project.name)['fields']])
            with self.assertRaises(frappe.ValidationError):
                task_config.update_task_fields(task.name, {fieldname: 'Review'})
            frappe.set_user('Administrator')
            restricted.reload(); restricted.mask = 1; restricted.save()
            self.assertNotIn(fieldname, task_config.get_task_fields(task.name)['values'])
            self.assertNotIn(fieldname, [field['fieldname'] for field in task_config.get_field_config(project.name)['fields']])
        finally:
            frappe.set_user('Administrator')
            if task and frappe.db.exists('Task', task.name): frappe.delete_doc('Task', task.name, force=True)
            if frappe.db.exists('Project', project.name): frappe.delete_doc('Project', project.name, force=True)
            if custom and frappe.db.exists('Custom Field', custom): frappe.delete_doc('Custom Field', custom, force=True)
            if reader and frappe.db.exists('User', reader): frappe.delete_doc('User', reader, force=True)
            # Native Custom Field schema changes commit DDL; explicitly clean fixtures.
            frappe.db.commit()
