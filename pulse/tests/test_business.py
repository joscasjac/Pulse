"""Business integration tests run against native ERPNext doctypes."""
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api.business import clone_template, capacity_hours, update_project, workload


class TestBusiness(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        from pulse.erpnext_bridge import ensure_default_company
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Template ' + frappe.generate_hash(length=8),
            'company': ensure_default_company(), 'pulse_is_template': 1}).insert()

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_clone_preserves_structure_but_resets_execution(self):
        parent = frappe.get_doc({'doctype': 'Task', 'subject': 'Parent', 'project': self.project.name, 'is_group': 1}).insert()
        prerequisite = frappe.get_doc({'doctype': 'Task', 'subject': 'Prerequisite', 'project': self.project.name}).insert()
        task = frappe.get_doc({'doctype': 'Task', 'subject': 'Child', 'project': self.project.name, 'parent_task': parent.name,
            'expected_time': 6, 'depends_on': [{'task': prerequisite.name}]}).insert()
        frappe.get_doc({'doctype': 'Pulse Checklist', 'task': task.name, 'item': 'Review', 'is_done': 1}).insert()
        frappe.get_doc({'doctype': 'Pulse Dependency', 'source_task': parent.name, 'target_task': task.name}).insert()
        result = clone_template(self.project.name, 'Copy ' + frappe.generate_hash(length=8))
        child = frappe.get_doc('Task', result['tasks'][task.name])
        self.assertEqual(child.parent_task, result['tasks'][parent.name])
        self.assertEqual(child.depends_on[0].task, result['tasks'][prerequisite.name])
        cloned_parent = frappe.get_doc('Task', result['tasks'][parent.name])
        self.assertIn(child.name, [row.task for row in cloned_parent.depends_on])
        self.assertEqual(child.expected_time, 6)
        self.assertEqual(child.status, 'Open')
        self.assertEqual(frappe.db.get_value('Pulse Checklist', {'task': child.name}, 'is_done'), 0)
        self.assertTrue(frappe.db.exists('Pulse Dependency', {'source_task': result['tasks'][parent.name], 'target_task': child.name}))
        again = clone_template(self.project.name, 'Copy again ' + frappe.generate_hash(length=8))
        self.assertNotEqual(result['project'], again['project'])

    def test_capacity_deduplicates_leave_and_caps_allocation(self):
        allocations = [dict(start_date='2026-09-14', end_date='2026-09-20', allocation_percentage=80)] * 2
        leaves = [dict(start_date='2026-09-15', end_date='2026-09-15')] * 2
        self.assertEqual(capacity_hours('2026-09-14', '2026-09-20', allocations, leaves), 32)

    def test_invalid_allocation_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({'doctype': 'Pulse Allocation', 'user': 'Administrator', 'project': self.project.name,
                'start_date': '2026-09-14', 'end_date': '2026-09-20', 'allocation_percentage': 101}).insert()

    def test_workload_requires_project_read(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            workload('2026-09-14', '2026-09-20', self.project.name)
        with self.assertRaises(frappe.PermissionError):
            clone_template(self.project.name, 'Forbidden')
        with self.assertRaises(frappe.PermissionError):
            update_project(self.project.name, is_template=0)

    def test_report_and_rest_exclude_private_project(self):
        from pulse.pulse.report.pulse_workload.pulse_workload import execute
        from frappe.client import get
        user = 'capacity-' + frappe.generate_hash(length=8) + '@example.com'
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Capacity Test', 'send_welcome_email': 0,
            'roles': [{'role': 'Pulse Senior Developer'}]}).insert()
        task = frappe.get_doc({'doctype': 'Task', 'subject': 'Hidden estimate', 'project': self.project.name, 'expected_time': 97}).insert()
        frappe.db.set_value('Task', task.name, '_assign', frappe.as_json([user]))
        frappe.set_user(user)
        self.assertEqual(execute({'start_date': '2026-09-14', 'end_date': '2026-09-20'})[1], [])
        with self.assertRaises(frappe.PermissionError):
            get('Project', self.project.name)
        with self.assertRaises(frappe.PermissionError):
            clone_template(self.project.name, 'Forbidden copy')

    def test_clone_remaps_labels_and_preserves_board_configuration(self):
        from pulse.api.task_config import save_config, save_label
        self.project.pulse_board_type = 'Kanban'
        self.project.pulse_enable_scrum = 0
        self.project.pulse_default_sprint_length = 21
        self.project.save()
        save_config(self.project.name, [
            {'label': 'Building', 'category': 'In Progress', 'color': '#123456'},
            {'label': 'Delivered', 'category': 'Done', 'color': '#654321'},
        ])
        label = save_label(self.project.name, 'Client review', '#abcdef')
        task = frappe.get_doc({'doctype': 'Task', 'subject': 'Configured task', 'project': self.project.name,
            'status': 'Working', 'workflow_state': 'Building', 'pulse_labels': [{'label': label['name']}]}).insert()
        result = clone_template(self.project.name, 'Configured copy ' + frappe.generate_hash(length=8))
        project = frappe.get_doc('Project', result['project'])
        copied = frappe.get_doc('Task', result['tasks'][task.name])
        self.assertEqual(project.pulse_board_type, 'Kanban')
        self.assertEqual(project.pulse_enable_scrum, 0)
        self.assertEqual(project.pulse_default_sprint_length, 21)
        self.assertEqual(copied.workflow_state, 'Building')
        self.assertEqual(copied.status, 'Working')
        self.assertNotEqual(copied.pulse_labels[0].label, label['name'])
        copied_label = frappe.get_doc('Pulse Label', copied.pulse_labels[0].label)
        self.assertEqual(copied_label.project, project.name)
        self.assertEqual(copied_label.label_name, 'Client review')
        self.assertEqual(copied_label.color, '#abcdef')

    def test_workload_omits_template_tasks_and_allocations(self):
        # Keep availability independent of retained browser QA / real user leave.
        user = 'template-load-' + frappe.generate_hash(length=8) + '@example.com'
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Template Load', 'send_welcome_email': 0,
            'roles': [{'role': 'Pulse Senior Developer'}]}).insert()
        live = frappe.get_doc({'doctype': 'Project', 'project_name': 'Capacity live ' + frappe.generate_hash(length=8),
            'company': self.project.company}).insert()
        for project, hours, percent in ((self.project.name, 91, 100), (live.name, 12, 50)):
            task = frappe.get_doc({'doctype': 'Task', 'subject': 'Estimated task', 'project': project,
                'expected_time': hours, 'exp_start_date': '2026-09-14', 'exp_end_date': '2026-09-18'}).insert()
            frappe.db.set_value('Task', task.name, '_assign', frappe.as_json([user]))
            frappe.get_doc({'doctype': 'Pulse Allocation', 'user': user, 'project': project,
                'status': 'Active', 'allocation_percentage': percent, 'start_date': '2026-09-14', 'end_date': '2026-09-18'}).insert()
        result = workload('2026-09-14', '2026-09-18', live.name)
        row = next(row for row in result['rows'] if row['user'] == user)
        self.assertEqual(row['estimated_hours'], 12)
        self.assertEqual(row['available_hours'], 20)
        self.assertEqual(workload('2026-09-14', '2026-09-18', self.project.name)['rows'], [])
        # A private test user sees only the two fixture projects: global totals
        # must not pull reusable plans into either estimates or capacity.
        for name in (self.project.name, live.name):
            doc = frappe.get_doc('Project', name)
            doc.append('users', {'user': user, 'welcome_email_sent': 1})
            doc.save()
        frappe.set_user(user)
        result = workload('2026-09-14', '2026-09-18')
        row = next(row for row in result['rows'] if row['user'] == user)
        self.assertEqual(row['estimated_hours'], 12)
        self.assertEqual(row['available_hours'], 20)

    def _commercial_records(self):
        # ERPNext's test helper imports bootstrap shared INR defaults. Explicit
        # unique native documents exercise the same controllers without altering
        # this site's configured currency or existing price lists.
        from frappe.utils import today, add_days
        suffix = frappe.generate_hash(length=8)
        group = frappe.get_doc({'doctype': 'Customer Group', 'customer_group_name': 'Pulse clients ' + suffix,
            'parent_customer_group': 'All Customer Groups', 'is_group': 0}).insert()
        def customer(name):
            return frappe.get_doc({'doctype': 'Customer', 'customer_name': name,
                'customer_type': 'Company', 'customer_group': group.name,
                'territory': 'All Territories'}).insert().name
        customer_name = customer('Pulse commercial ' + suffix)
        other_customer = customer('Pulse other customer ' + suffix)
        item = frappe.get_doc({'doctype': 'Item', 'item_code': 'Pulse service ' + suffix,
            'item_name': 'Pulse service ' + suffix, 'item_group': 'All Item Groups',
            'is_stock_item': 0, 'stock_uom': 'Nos'}).insert()
        currency = frappe.db.get_value('Company', self.project.company, 'default_currency')
        price_list = frappe.get_doc({'doctype': 'Price List', 'price_list_name': 'Pulse commercial ' + suffix,
            'currency': currency, 'enabled': 1, 'selling': 1}).insert()
        order = frappe.get_doc({'doctype': 'Sales Order', 'company': self.project.company,
            'customer': customer_name, 'transaction_date': today(), 'delivery_date': add_days(today(), 10),
            'currency': currency, 'conversion_rate': 1, 'selling_price_list': price_list.name,
            'price_list_currency': currency, 'plc_conversion_rate': 1,
            'items': [{'item_code': item.name, 'qty': 1, 'rate': 100, 'uom': 'Nos', 'conversion_factor': 1}]}).insert()
        return customer_name, other_customer, order

    def test_commercial_links_match_and_reject_mismatch_on_api_and_rest(self):
        from frappe.client import save
        customer, other_customer, order = self._commercial_records()
        update_project(self.project.name, customer=customer, sales_order=order.name, is_template=1)
        self.project.reload()
        self.assertEqual(self.project.customer, customer)
        self.assertEqual(self.project.sales_order, order.name)
        with self.assertRaises(frappe.ValidationError):
            update_project(self.project.name, customer=other_customer, sales_order=order.name)
        self.project.reload()
        self.assertEqual(self.project.customer, customer)
        data = self.project.as_dict()
        data['customer'] = other_customer
        with self.assertRaises(frappe.ValidationError):
            save(frappe.as_json(data))
        self.project.reload()
        self.assertEqual(self.project.customer, customer)
        self.assertEqual(self.project.sales_order, order.name)

    def test_commercial_links_deny_unreadable_customer_and_order(self):
        from frappe.client import save
        from pulse.api.business import commercial_options
        customer, other_customer, order = self._commercial_records()
        user = 'commercial-' + frappe.generate_hash(length=8) + '@example.com'
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Commercial Test', 'send_welcome_email': 0,
            'roles': [{'role': 'Pulse Manager'}]}).insert()
        self.project.append('users', {'user': user, 'welcome_email_sent': 1})
        self.project.save()
        frappe.set_user(user)
        self.assertTrue(frappe.has_permission('Project', 'write', doc=self.project.name))
        self.assertFalse(frappe.has_permission('Customer', 'read', doc=customer))
        self.assertFalse(frappe.has_permission('Sales Order', 'read', doc=order.name))
        self.assertEqual(commercial_options(customer)['customers'], [])
        self.assertEqual(commercial_options(customer)['orders'], [])
        with self.assertRaises(frappe.PermissionError):
            update_project(self.project.name, customer=customer)
        with self.assertRaises(frappe.PermissionError):
            update_project(self.project.name, sales_order=order.name)
        data = frappe.get_doc('Project', self.project.name).as_dict()
        data['customer'], data['sales_order'] = customer, order.name
        with self.assertRaises(frappe.PermissionError):
            save(frappe.as_json(data))
        frappe.set_user('Administrator')
        self.project.reload()
        self.assertFalse(self.project.customer)
        self.assertFalse(self.project.sales_order)
