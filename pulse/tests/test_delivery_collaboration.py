"""Real native record/share boundaries for handoffs and external collaboration."""
import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch
from pulse.api import handoffs, external


class TestDeliveryCollaboration(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.mail = patch('frappe.sendmail'); self.mail.start(); self.addCleanup(self.mail.stop)
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'External acceptance ' + frappe.generate_hash(length=8)}).insert()
        self.task = frappe.get_doc({'doctype': 'Task', 'subject': 'Shared delivery milestone', 'project': self.project.name,
            'description': 'INTERNAL DESCRIPTION MUST NOT LEAK'}).insert()
        self.hidden = frappe.get_doc({'doctype': 'Task', 'subject': 'Hidden task', 'project': self.project.name}).insert()
        self.external = 'external-' + frappe.generate_hash(length=8) + '@example.test'
        frappe.get_doc({'doctype': 'User', 'email': self.external, 'first_name': 'External Participant',
            'user_type': 'Website User', 'enabled': 1, 'send_welcome_email': 0}).insert()

    def tearDown(self):
        frappe.set_user('Administrator'); frappe.db.rollback()

    def test_explicit_share_exposes_only_narrow_fields_and_separate_comments(self):
        external.share(self.task.name, self.external)
        frappe.get_doc({'doctype':'Pulse Comment','task':self.task.name,'comment_text':'INTERNAL COMMENT'}).insert()
        frappe.set_user(self.external)
        self.assertFalse(frappe.has_permission('Task', 'read', doc=self.task.name))
        from frappe.client import get
        with self.assertRaises(frappe.PermissionError): get('Task', self.task.name)
        with self.assertRaises(frappe.PermissionError): get('Project', self.project.name)
        rows = external.shared_tasks()
        self.assertEqual([r['name'] for r in rows], [self.task.name])
        self.assertNotIn('description', rows[0]); self.assertNotIn('assignees', rows[0]); self.assertNotIn('project', rows[0])
        with self.assertRaises(frappe.PermissionError): external.task(self.hidden.name)
        with self.assertRaises(frappe.PermissionError): external.comment(self.hidden.name, 'denied')
        name = external.comment(self.task.name, '<script>plain text</script>')
        response = external.task(self.task.name)
        self.assertEqual(response['comments'][0]['name'], name)
        self.assertNotIn('owner', response['comments'][0])
        self.assertNotIn('INTERNAL', str(response))
        with self.assertRaises(frappe.PermissionError): external.sharing(self.task.name)
        frappe.set_user('Administrator'); external.reply(self.task.name, 'External reply')
        self.assertEqual(len(external.discussion(self.task.name)), 2)
        external.revoke(self.task.name, self.external)
        frappe.set_user(self.external)
        self.assertEqual(external.shared_tasks(), [])
        with self.assertRaises(frappe.PermissionError): external.task(self.task.name)

    def test_guest_and_disabled_user_cannot_use_portal(self):
        external.share(self.task.name, self.external)
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError): external.shared_tasks()
        frappe.set_user('Administrator'); frappe.db.set_value('User', self.external, 'enabled', 0)
        frappe.set_user(self.external)
        with self.assertRaises(frappe.PermissionError): external.task(self.task.name)

    def test_revocation_before_locked_grant_check_prevents_external_comment(self):
        external.share(self.task.name, self.external)
        grant = frappe.db.get_value('Pulse External Share', {'task': self.task.name, 'user': self.external}, 'name')
        frappe.set_user(self.external)
        original = frappe.db.get_value
        injected = []
        def revoked_at_boundary(doctype, *args, **kwargs):
            if doctype == 'Pulse External Share' and kwargs.get('for_update') and not injected:
                injected.append(True)
                frappe.db.set_value('Pulse External Share', grant, 'enabled', 0)
            return original(doctype, *args, **kwargs)
        with patch.object(frappe.db, 'get_value', side_effect=revoked_at_boundary):
            with self.assertRaises(frappe.PermissionError):
                external.comment(self.task.name, 'Must not be posted after revocation')
        self.assertEqual(len(injected), 1)
        self.assertFalse(frappe.db.exists('Pulse External Comment', {'task': self.task.name}))

    def test_handoff_retries_return_same_native_project_and_template_tasks(self):
        # Reuse the native commercial fixture factory, not a mocked Sales Order.
        from pulse.tests.test_business import TestBusiness
        fixture = TestBusiness(); fixture.project = self.project
        customer, _, order = fixture._commercial_records()
        with self.assertRaises(frappe.ValidationError):
            handoffs.create('Sales Order', order.name, 'Not submitted')
        order.submit()
        self.project.reload(); self.project.pulse_is_template = 1; self.project.save()
        first = handoffs.create('Sales Order', order.name, 'Delivery handoff', template=self.project.name)
        second = handoffs.create('Sales Order', order.name, 'Ignored retry title')
        self.assertTrue(first['created']); self.assertFalse(second['created'])
        self.assertEqual(first['project'], second['project'])
        target = frappe.get_doc('Project', first['project'])
        self.assertEqual(target.customer, customer); self.assertEqual(target.sales_order, order.name)
        self.assertEqual(frappe.db.count('Task', {'project': target.name}), 2)
        self.assertEqual(handoffs.existing('Sales Order', order.name)['project'], target.name)
        frappe.set_user(self.external)
        with self.assertRaises(frappe.PermissionError): handoffs.create('Sales Order', order.name, 'Denied')

    def test_failed_handoff_rolls_back_created_project_and_mapping(self):
        from pulse.tests.test_business import TestBusiness
        fixture = TestBusiness(); fixture.project = self.project
        _, _, order = fixture._commercial_records(); order.submit()
        before = frappe.db.count('Project')
        original = frappe.get_doc
        def fail_mapping(*args, **kwargs):
            if args and isinstance(args[0], dict) and args[0].get('doctype') == 'Pulse Business Handoff':
                raise frappe.ValidationError('Injected mapping failure')
            return original(*args, **kwargs)
        with patch('frappe.get_doc', side_effect=fail_mapping):
            with self.assertRaises(frappe.ValidationError): handoffs.create('Sales Order', order.name, 'Rollback')
        self.assertEqual(frappe.db.count('Project'), before)
        self.assertFalse(frappe.db.exists('Pulse Business Handoff', handoffs._identity('Sales Order', order.name)))

    def test_template_copies_configured_custom_fields_and_stage_rules(self):
        from pulse.api.task_config import create_custom_task_field, save_field_config
        from pulse.api.business import clone_template
        result = None; fieldname = None
        try:
            field = create_custom_task_field(self.project.name, 'Delivery reference ' + frappe.generate_hash(length=6), 'Data')
            fieldname = field['fieldname']
            save_field_config(self.project.name, [{'fieldname': fieldname, 'show_in_form': 1, 'required_statuses': 'To Do'}], approval_statuses=['Done'])
            self.project.reload(); self.project.pulse_is_template = 1; self.project.save()
            self.task = frappe.get_doc('Task', self.task.name); self.task.set(fieldname, 'DELIVERY-123'); self.task.save()
            self.hidden = frappe.get_doc('Task', self.hidden.name); self.hidden.set(fieldname, 'DELIVERY-456'); self.hidden.save()
            result = clone_template(self.project.name, 'Configured clone')
            target = frappe.get_doc('Project', result['project'])
            self.assertEqual(target.pulse_approval_statuses, 'Done')
            self.assertEqual(target.pulse_task_field_rules[0].fieldname, fieldname)
            self.assertEqual(frappe.db.get_value('Task', result['tasks'][self.task.name], fieldname), 'DELIVERY-123')
        finally:
            # Native Custom Field creation commits DDL; cleanup all committed fixtures.
            projects = [self.project.name] + ([result['project']] if result else [])
            for project in projects:
                for task in frappe.get_all('Task', filters={'project': project}, pluck='name'):
                    frappe.delete_doc('Task', task, force=True)
                if frappe.db.exists('Project', project): frappe.delete_doc('Project', project, force=True)
            if frappe.db.exists('User', self.external): frappe.delete_doc('User', self.external, force=True)
            custom = frappe.db.get_value('Custom Field', {'dt':'Task','fieldname':fieldname}, 'name') if fieldname else None
            if custom: frappe.delete_doc('Custom Field', custom, force=True)
            frappe.db.commit()

    def test_handoff_adopts_existing_native_order_project_instead_of_duplicate(self):
        from pulse.tests.test_business import TestBusiness
        fixture = TestBusiness(); fixture.project = self.project
        customer, _, order = fixture._commercial_records(); order.submit()
        self.project.reload(); self.project.customer = customer; self.project.sales_order = order.name; self.project.save()
        before = frappe.db.count('Project')
        result = handoffs.create('Sales Order', order.name, 'Should reuse linked project')
        self.assertFalse(result['created']); self.assertEqual(result['project'], self.project.name)
        self.assertEqual(frappe.db.count('Project'), before)

    def test_record_identifiers_reject_filter_operators(self):
        for value in (['like', '%'], {'name': self.task.name}, '', None):
            with self.assertRaises(frappe.ValidationError): external.share(self.task.name, value)
            with self.assertRaises(frappe.ValidationError): external.revoke(self.task.name, value)
            with self.assertRaises(frappe.ValidationError): external.task(value)
            with self.assertRaises(frappe.ValidationError): handoffs.existing('Sales Order', value)
        self.assertFalse(frappe.db.exists('Pulse External Share', {'task': self.task.name}))
