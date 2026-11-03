"""Required custom values must be accepted on the first native Task save."""
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api import recurring, spa, task_config


class TestFirstSaveCompanyFields(IntegrationTestCase):
    def test_required_custom_field_creation_permissions_and_recurring_guard(self):
        frappe.set_user('Administrator')
        project = frappe.get_doc({'doctype': 'Project', 'project_name': 'First save fields ' + frappe.generate_hash(length=8)}).insert()
        created = []; custom = None; user = None
        try:
            field = task_config.create_custom_task_field(project.name, 'First save ' + frappe.generate_hash(length=8), 'Select', 'Review\nReady')
            fieldname = field['fieldname']; custom = 'Task-' + fieldname
            task_config.save_field_config(project.name, [{'fieldname': fieldname, 'show_in_form': 1, 'required_statuses': 'Backlog\nTo Do'}])
            metadata = task_config.get_creation_fields(project.name)
            self.assertEqual([row['fieldname'] for row in metadata['fields']], [fieldname])
            self.assertEqual(metadata['fields'][0]['required_statuses'], ['Backlog', 'To Do'])
            self.assertTrue(metadata['recurring_custom_fields_required'])
            before = frappe.db.count('Task', {'project': project.name})
            with self.assertRaisesRegex(frappe.ValidationError, 'full New task form'):
                spa.create_task(project.name, 'Inline missing required field')
            self.assertEqual(frappe.db.count('Task', {'project': project.name}), before)
            for values in ({'owner': 'Guest'}, {'subject': 'Override'}, {'custom_unconfigured': 'No'}, [], '{invalid-json', {fieldname: ['Invalid scalar']}, {fieldname: float('nan')}, {fieldname: 'Not a configured choice'}):
                with self.assertRaises(frappe.ValidationError):
                    spa.create_task(project.name, 'Reject forbidden values', field_values=values)
            result = spa.create_task(project.name, 'Complete on first save', field_values={fieldname: 'Ready'})
            created.append(result['name'])
            self.assertEqual(frappe.get_doc('Task', result['name']).get(fieldname), 'Ready')
            inactive = frappe.get_doc({'doctype': 'Pulse Recurring Task', 'subject': 'Inactive unsupported template', 'project': project.name, 'interval_count': 1, 'interval_unit': 'Week', 'is_active': 0}).insert()
            with self.assertRaisesRegex(frappe.ValidationError, 'one-off task'):
                recurring.update_recurring(inactive.name, description='Do not save')
            with self.assertRaisesRegex(frappe.ValidationError, 'one-off task'):
                recurring.toggle_recurring(inactive.name, 1)
            self.assertFalse(frappe.db.get_value('Pulse Recurring Task', inactive.name, 'is_active'))
            recurring_before = frappe.db.count('Pulse Recurring Task', {'project': project.name})
            with self.assertRaisesRegex(frappe.ValidationError, 'one-off task'):
                recurring.create_recurring('Cannot persist unsupported template', project.name)
            self.assertEqual(frappe.db.count('Pulse Recurring Task', {'project': project.name}), recurring_before)
            user = 'first-save-reader-' + frappe.generate_hash(length=8) + '@example.test'
            frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Creator', 'send_welcome_email': 0,
                'roles': [{'role': 'Projects User'}]}).insert()
            frappe.db.set_value('Project', project.name, 'owner', user)
            frappe.clear_document_cache('Project', project.name)
            restricted = frappe.get_doc('Custom Field', custom); restricted.permlevel = 1; restricted.save()
            frappe.set_user(user)
            self.assertEqual(task_config.get_creation_fields(project.name)['fields'], [])
            with self.assertRaises(frappe.ValidationError):
                spa.create_task(project.name, 'Cannot set hidden field', field_values={fieldname: 'Ready'})
            with self.assertRaisesRegex(frappe.ValidationError, 'current access'):
                spa.create_task(project.name, 'Cannot satisfy hidden requirement')
            frappe.set_user('Administrator')
            restricted.reload(); restricted.mask = 1; restricted.save()
            self.assertEqual(task_config.get_creation_fields(project.name)['fields'], [])
            with self.assertRaises(frappe.ValidationError):
                spa.create_task(project.name, 'Cannot set masked field', field_values={fieldname: 'Ready'})
        finally:
            frappe.set_user('Administrator')
            for name in created:
                if frappe.db.exists('Task', name): frappe.delete_doc('Task', name, force=True)
            # Also remove any unexpected failed-create residue to keep QA reusable.
            for name in frappe.get_all('Task', filters={'project': project.name}, pluck='name'):
                frappe.delete_doc('Task', name, force=True)
            for name in frappe.get_all('Pulse Recurring Task', filters={'project': project.name}, pluck='name'):
                frappe.delete_doc('Pulse Recurring Task', name, force=True)
            if frappe.db.exists('Project', project.name): frappe.delete_doc('Project', project.name, force=True)
            if custom and frappe.db.exists('Custom Field', custom): frappe.delete_doc('Custom Field', custom, force=True)
            if user and frappe.db.exists('User', user): frappe.delete_doc('User', user, force=True)
            # Native Custom Field DDL commits, so clean these unique fixtures explicitly.
            frappe.db.commit()


class TestRecurringInitialApprovalGuard(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_approval_required_initial_status_cannot_create_orphan_template(self):
        frappe.set_user('Administrator')
        project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Recurring approval ' + frappe.generate_hash(length=8),
            'pulse_approval_statuses': 'To Do'}).insert()
        self.assertTrue(task_config.get_creation_fields(project.name)['recurring_approval_required'])
        with self.assertRaisesRegex(frappe.ValidationError, 'requires approval'):
            recurring.create_recurring('Unapproved recurring task', project.name)
        self.assertEqual(frappe.db.count('Pulse Recurring Task', {'project': project.name}), 0)

    def test_active_templates_block_incompatible_rule_changes_until_deactivated(self):
        from unittest.mock import patch
        frappe.set_user('Administrator')
        project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Recurring config guard ' + frappe.generate_hash(length=8)}).insert()
        template = frappe.get_doc({'doctype': 'Pulse Recurring Task', 'project': project.name,
            'subject': 'Existing scheduled work', 'interval_count': 1, 'interval_unit': 'Week', 'is_active': 1}).insert()
        required_start = [{'fieldname': 'exp_start_date', 'show_in_form': 1, 'required_statuses': 'To Do'}]
        with self.assertRaises(frappe.ValidationError):
            task_config.save_field_config(project.name, required_start)
        self.assertFalse(frappe.get_doc('Project', project.name).get('pulse_task_field_rules'))
        with self.assertRaisesRegex(frappe.ValidationError, 'requires approval'):
            task_config.save_field_config(project.name, [], approval_statuses=['To Do'])
        self.assertFalse(frappe.get_doc('Project', project.name).get('pulse_approval_statuses'))
        self.assertTrue(frappe.db.get_value('Pulse Recurring Task', template.name, 'is_active'))
        # Use the actual disable API while preventing its legacy explicit fixture commit.
        with patch.object(frappe.db, 'commit'):
            recurring.toggle_recurring(template.name, 0)
        task_config.save_field_config(project.name, required_start)
        rules = frappe.get_doc('Project', project.name).get('pulse_task_field_rules')
        self.assertEqual([row.fieldname for row in rules], ['exp_start_date'])
        with self.assertRaises(frappe.ValidationError):
            recurring.toggle_recurring(template.name, 1)
        self.assertFalse(frappe.db.get_value('Pulse Recurring Task', template.name, 'is_active'))
