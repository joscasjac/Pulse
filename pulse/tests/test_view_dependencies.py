"""Timeline reads native task dependencies without leaking hidden endpoints."""
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api.views import tasks


class TestViewDependencies(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        from pulse.erpnext_bridge import ensure_default_company
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'View edges ' + frappe.generate_hash(length=8),
                                       'company': ensure_default_company()}).insert()
        self.prerequisite = frappe.get_doc({'doctype': 'Task', 'subject': 'Prerequisite', 'project': self.project.name}).insert()
        self.dependent = frappe.get_doc({'doctype': 'Task', 'subject': 'Dependent', 'project': self.project.name,
                                        'depends_on': [{'task': self.prerequisite.name}]}).insert()

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def result(self):
        return tasks({'filter': {'field': 'project', 'op': 'eq', 'value': self.project.name}})

    def test_native_only_edge_preserves_direction_and_source(self):
        edges = self.result()['dependencies']
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source_task'], self.dependent.name)
        self.assertEqual(edges[0]['target_task'], self.prerequisite.name)
        self.assertEqual(edges[0]['sources'], ['erpnext'])
        self.assertTrue(edges[0]['name'].startswith('native:'))
        self.assertEqual(edges[0]['native_name'], self.dependent.depends_on[0].name)
        self.assertFalse(frappe.db.exists('Pulse Dependency', {'source_task': self.dependent.name}))

    def test_duplicate_pulse_and_native_edge_is_returned_once(self):
        edge = frappe.get_doc({'doctype': 'Pulse Dependency', 'source_task': self.dependent.name,
                               'target_task': self.prerequisite.name, 'source_project': self.project.name,
                               'target_project': self.project.name}).insert()
        edges = self.result()['dependencies']
        self.assertEqual(len(edges), 1)
        self.assertEqual(set(edges[0]['sources']), {'pulse', 'erpnext'})
        self.assertEqual(edges[0]['pulse_name'], edge.name)
        self.assertEqual(edges[0]['name'], edge.name)
        self.dependent.set('depends_on', [])
        self.dependent.save()
        self.assertEqual(self.result()['dependencies'][0]['sources'], ['pulse'])

    def test_hidden_native_prerequisite_is_not_disclosed(self):
        user = 'view-edge-' + frappe.generate_hash(length=8) + '@example.com'
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Edges', 'send_welcome_email': 0,
                        'roles': [{'role': 'Pulse Junior Developer'}]}).insert()
        self.project.reload()
        self.project.append('users', {'user': user, 'welcome_email_sent': 1})
        self.project.save()
        self.dependent.db_set('owner', user)
        frappe.set_user(user)
        result = self.result()
        self.assertIn(self.dependent.name, [task.name for task in result['tasks']])
        self.assertNotIn(self.prerequisite.name, [task.name for task in result['tasks']])
        self.assertEqual(result['dependencies'], [])

    def test_filter_excluding_one_endpoint_removes_native_edge(self):
        result = tasks({'filter': {'field': 'subject', 'op': 'eq', 'value': self.dependent.subject}})
        self.assertEqual(result['dependencies'], [])

    def test_analytics_counts_native_dependency_but_not_review_alone(self):
        from pulse.api.analytics import get_analytics
        self.dependent.workflow_state = 'In Review'
        self.dependent.save()
        self.assertEqual(get_analytics(self.project.name)['kpis']['blocked'], 1)
        self.prerequisite.workflow_state = 'Done'
        self.prerequisite.save()
        self.assertEqual(get_analytics(self.project.name)['kpis']['blocked'], 0)

    def test_analytics_resolved_pulse_edge_does_not_override_native_edge(self):
        from pulse.api.analytics import get_analytics
        frappe.get_doc({'doctype': 'Pulse Dependency', 'source_task': self.dependent.name,
                        'target_task': self.prerequisite.name, 'source_project': self.project.name,
                        'target_project': self.project.name, 'status': 'Resolved'}).insert()
        self.assertEqual(get_analytics(self.project.name)['kpis']['blocked'], 1)
        self.dependent.set('depends_on', [])
        self.dependent.save()
        self.assertEqual(get_analytics(self.project.name)['kpis']['blocked'], 0)

    def test_analytics_hidden_native_target_does_not_leak_blocker(self):
        from pulse.api.analytics import get_analytics
        user = 'analytics-edge-' + frappe.generate_hash(length=8) + '@example.com'
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Edges', 'send_welcome_email': 0,
                        'roles': [{'role': 'Pulse Junior Developer'}]}).insert()
        self.project.reload()
        self.project.append('users', {'user': user, 'welcome_email_sent': 1})
        self.project.save()
        self.dependent.db_set('owner', user)
        frappe.set_user(user)
        self.assertEqual(get_analytics(self.project.name)['kpis']['blocked'], 0)
        from pulse.api.spa import get_task
        self.assertEqual(get_task(self.dependent.name)['blocked_by'], [])

    def test_drawer_native_edge_retains_direction_and_provenance(self):
        from pulse.api.spa import get_task
        blockers = get_task(self.dependent.name)['blocked_by']
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]['task'], self.prerequisite.name)
        self.assertEqual(blockers[0]['subject'], self.prerequisite.subject)
        self.assertEqual(blockers[0]['sources'], ['erpnext'])
        self.assertFalse(blockers[0]['can_remove'])
        self.assertEqual(get_task(self.prerequisite.name)['blocked_by'], [])
