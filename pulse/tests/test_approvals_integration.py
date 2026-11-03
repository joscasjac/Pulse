import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch
from pulse.api import approvals, task_config


class TestTaskApprovals(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.mail = patch('frappe.sendmail'); self.mail.start(); self.addCleanup(self.mail.stop)
        self.reviewer = 'approval-reviewer-' + frappe.generate_hash(length=8) + '@example.test'
        frappe.get_doc({'doctype': 'User', 'email': self.reviewer, 'first_name': 'Reviewer', 'enabled': 1,
            'user_type': 'System User', 'send_welcome_email': 0, 'roles': [{'role': 'Projects User'}]}).insert()
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Approval ' + frappe.generate_hash(length=8)}).insert()
        frappe.db.set_value('Project', self.project.name, 'owner', self.reviewer)
        self.task = frappe.get_doc({'doctype': 'Task', 'subject': 'Review current work', 'project': self.project.name}).insert()

    def tearDown(self):
        frappe.set_user('Administrator'); frappe.db.rollback()

    def test_request_is_idempotent_and_approval_unlocks_native_status(self):
        task_config.save_field_config(self.project.name, [], approval_statuses=['Done'])
        with self.assertRaises(frappe.ValidationError):
            self.task.workflow_state = 'Done'; self.task.save()
        self.task.reload()
        first = approvals.request_approval(self.task.name, self.reviewer)
        second = approvals.request_approval(self.task.name, self.reviewer)
        self.assertEqual(first, second)
        self.assertEqual(frappe.db.count('Pulse Task Approval', {'task': self.task.name}), 1)
        frappe.set_user(self.reviewer)
        self.assertTrue(approvals.get_approvals(self.task.name)['approvals'][0]['can_decide'])
        approvals.decide(first['name'], 'Approved', 'Ready to deliver')
        self.task.reload(); self.task.workflow_state = 'Done'; self.task.save()
        self.assertEqual(self.task.status, 'Completed')
        record = frappe.get_doc('Pulse Task Approval', first['name'])
        self.assertEqual(record.decided_by, self.reviewer)
        self.assertEqual(record.note, 'Ready to deliver')

    def test_changed_content_invalidates_pending_and_completed_approval(self):
        request = approvals.request_approval(self.task.name, self.reviewer)
        self.task.subject = 'Changed content'; self.task.save()
        frappe.set_user(self.reviewer)
        with self.assertRaises(frappe.ValidationError):
            approvals.decide(request['name'], 'Approved')
        frappe.set_user('Administrator')
        current = approvals.request_approval(self.task.name, self.reviewer)
        frappe.set_user(self.reviewer); approvals.decide(current['name'], 'Approved')
        frappe.set_user('Administrator'); task_config.save_field_config(self.project.name, [], approval_statuses=['Done'])
        self.task.reload(); self.task.description = 'New material'; self.task.workflow_state = 'Done'
        with self.assertRaises(frappe.ValidationError):
            self.task.save()

    def test_self_approval_wrong_reviewer_and_direct_record_tampering_denied(self):
        with self.assertRaises(frappe.PermissionError):
            approvals.request_approval(self.task.name, 'Administrator')
        request = approvals.request_approval(self.task.name, self.reviewer)
        with self.assertRaises(frappe.PermissionError):
            approvals.decide(request['name'], 'Approved')
        record = frappe.get_doc('Pulse Task Approval', request['name']); record.decision = 'Approved'
        with self.assertRaises(frappe.PermissionError):
            record.save(ignore_permissions=True)
        frappe.set_user(self.reviewer); approvals.decide(request['name'], 'Rejected', 'Needs correction')
        with self.assertRaises(frappe.ValidationError):
            approvals.decide(request['name'], 'Approved')

    def test_hidden_task_cannot_be_read_or_reviewed(self):
        request = approvals.request_approval(self.task.name, self.reviewer)
        frappe.set_user('Guest')
        for action in (lambda: approvals.get_approvals(self.task.name),
                       lambda: approvals.request_approval(self.task.name, self.reviewer),
                       lambda: approvals.decide(request['name'], 'Approved')):
            with self.assertRaises(frappe.PermissionError):
                action()

    def test_disabled_or_revoked_reviewer_cannot_decide(self):
        request = approvals.request_approval(self.task.name, self.reviewer)
        frappe.db.set_value('User', self.reviewer, 'enabled', 0)
        frappe.set_user(self.reviewer)
        with self.assertRaises(frappe.PermissionError):
            approvals.decide(request['name'], 'Approved')
        frappe.set_user('Administrator'); frappe.db.set_value('User', self.reviewer, 'enabled', 1)
        frappe.db.set_value('Project', self.project.name, 'owner', 'Administrator')
        frappe.clear_document_cache('Project', self.project.name)
        frappe.set_user(self.reviewer)
        with self.assertRaises(frappe.PermissionError):
            approvals.decide(request['name'], 'Approved')

    def test_notification_failure_does_not_leave_partial_request_or_decision(self):
        with patch('pulse.api.approvals._notify', side_effect=frappe.ValidationError('Notification rejected')):
            with self.assertRaises(frappe.ValidationError):
                approvals.request_approval(self.task.name, self.reviewer)
        self.assertFalse(frappe.db.exists('Pulse Task Approval', {'task': self.task.name}))
        request = approvals.request_approval(self.task.name, self.reviewer)
        frappe.set_user(self.reviewer)
        with patch('pulse.api.approvals._notify', side_effect=frappe.ValidationError('Notification rejected')):
            with self.assertRaises(frappe.ValidationError):
                approvals.decide(request['name'], 'Approved')
        self.assertEqual(frappe.db.get_value('Pulse Task Approval', request['name'], 'decision'), 'Pending')

    def test_revoking_completed_reviewer_access_blocks_required_stage(self):
        request = approvals.request_approval(self.task.name, self.reviewer)
        frappe.set_user(self.reviewer); approvals.decide(request['name'], 'Approved')
        frappe.set_user('Administrator'); task_config.save_field_config(self.project.name, [], approval_statuses=['Done'])
        frappe.db.set_value('User', self.reviewer, 'enabled', 0)
        self.task.reload(); self.task.workflow_state = 'Done'
        with self.assertRaises(frappe.ValidationError):
            self.task.save()
        frappe.db.set_value('User', self.reviewer, 'enabled', 1)
        frappe.db.set_value('Project', self.project.name, 'owner', 'Administrator')
        frappe.clear_document_cache('Project', self.project.name)
        with self.assertRaises(frappe.ValidationError):
            self.task.save()

    def test_configuration_keeps_an_initial_status_without_prior_approval(self):
        stages = [row['label'] for row in task_config.statuses_for(self.project)]
        with self.assertRaises(frappe.ValidationError):
            task_config.save_field_config(self.project.name, [], approval_statuses=stages)
