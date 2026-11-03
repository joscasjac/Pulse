import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import Mock, patch
from pulse.api import team
from pulse.api.automation import execute


class TestProjectTeam(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.mail = patch('frappe.sendmail')
        self.mail.start()
        self.addCleanup(self.mail.stop)
        self.users = []
        for label in ('departing', 'replacement'):
            email = label + '-' + frappe.generate_hash(length=8) + '@example.test'
            frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': label,
                'enabled': 1, 'user_type': 'System User', 'send_welcome_email': 0,
                'roles': [{'role': 'Projects User'}]}).insert()
            self.users.append(email)
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Team acceptance ' + frappe.generate_hash(length=8),
            'users': [{'user': user} for user in self.users]}).insert()
        self.task = frappe.get_doc({'doctype': 'Task', 'project': self.project.name, 'subject': 'Handoff'}).insert()
        from frappe.desk.form.assign_to import add
        add({'doctype': 'Task', 'name': self.task.name, 'assign_to': [self.users[0]]})

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_member_add_is_idempotent_and_handoff_updates_native_assignments(self):
        result = execute('add_project_member', {'project': self.project.name, 'user': self.users[0]})
        self.assertEqual(len(execute('get_project_team', {'project': self.project.name})['members']), 2)
        self.assertEqual(len(result['members']), 2)
        result = execute('remove_project_member', {'project': self.project.name, 'user': self.users[0], 'replacement': self.users[1]})
        self.assertEqual(result['tasks'], [self.task.name])
        self.assertEqual([row.user for row in frappe.get_doc('Project', self.project.name).users], [self.users[1]])
        self.assertFalse(frappe.db.exists('ToDo', {'reference_name': self.task.name, 'allocated_to': self.users[0], 'status': 'Open'}))
        self.assertTrue(frappe.db.exists('ToDo', {'reference_name': self.task.name, 'allocated_to': self.users[1], 'status': 'Open'}))

    def test_handoff_failure_rolls_back_membership_and_assignments(self):
        with patch('pulse.api.tasks.bulk_update', side_effect=frappe.ValidationError('Assignment rejected')):
            with self.assertRaises(frappe.ValidationError):
                team.remove_member(self.project.name, self.users[0], self.users[1])
        self.assertEqual(len(frappe.get_doc('Project', self.project.name).users), 2)
        self.assertTrue(frappe.db.exists('ToDo', {'reference_name': self.task.name, 'allocated_to': self.users[0], 'status': 'Open'}))

    def test_non_admin_cannot_manage_team_even_when_member(self):
        frappe.set_user(self.users[0])
        for action in (lambda: team.get_team(self.project.name), lambda: team.add_member(self.project.name, self.users[1]),
                       lambda: team.remove_member(self.project.name, self.users[1])):
            with self.assertRaises(frappe.PermissionError):
                action()

    def test_cannot_handoff_to_self_or_remove_project_owner(self):
        with self.assertRaises(frappe.ValidationError):
            team.remove_member(self.project.name, self.users[0], self.users[0])
        with self.assertRaises(frappe.ValidationError):
            team.remove_member(self.project.name, 'Administrator')

    def test_owner_transfer_requires_existing_member_and_preserves_tasks(self):
        result = execute('transfer_project_owner', {'project': self.project.name, 'user': self.users[1]})
        self.assertTrue(frappe.db.exists('Pulse Activity Log', {'project': self.project.name, 'activity_type': 'Project Ownership Changed'}))
        self.assertEqual(result['previous_owner'], 'Administrator')
        self.assertEqual(frappe.get_doc('Project', self.project.name).owner, self.users[1])
        self.assertEqual(frappe.get_doc('Task', self.task.name).project, self.project.name)
        with self.assertRaises(frappe.ValidationError):
            team.remove_member(self.project.name, self.users[1])
        with self.assertRaises(frappe.ValidationError):
            team.transfer_owner(self.project.name, 'Guest')

    def test_invite_creates_minimal_role_and_project_member(self):
        email = 'invited-' + frappe.generate_hash(length=8) + '@example.test'
        result = team.invite_member(self.project.name, email, 'Invited', 'Member')
        self.assertEqual(result['user'], email)
        self.assertTrue(result['welcome_email_queued'])
        user = frappe.get_doc('User', email)
        self.assertEqual(user.user_type, 'System User')
        self.assertIn('Projects User', [row.role for row in user.roles])
        self.assertIn('Pulse Junior Developer', [row.role for row in user.roles])
        self.assertNotIn('System Manager', [row.role for row in user.roles])
        self.assertNotIn('Pulse Admin', [row.role for row in user.roles])
        self.assertNotIn('Pulse Manager', [row.role for row in user.roles])
        self.assertIn(email, [r.user for r in frappe.get_doc('Project', self.project.name).users])
        with self.assertRaises(frappe.ValidationError):
            team.invite_member(self.project.name, email, 'Again')
        # Prove the default account can use the application, not just native Task.
        from pulse.api import spa, task_config, modules
        frappe.set_user(email)
        self.assertTrue(task_config.get_config(self.project.name)['statuses'])
        with patch.object(frappe.db, 'commit'):
            created = spa.create_task(self.project.name, 'Invited contributor task', assignees=[email])
        detail = spa.get_task(created['name'])
        self.assertTrue(detail['can_write'])
        self.assertIn(email, detail['assignees'])
        module = modules.save_module(self.project.name, 'Contributor delivery module')
        modules.set_tasks(module['name'], [created['name']])
        self.assertEqual([task['name'] for task in modules.get_module(module['name'])['tasks']], [created['name']])

    def test_invitation_failure_does_not_leave_user_or_member(self):
        email = 'failed-invite-' + frappe.generate_hash(length=8) + '@example.test'
        with patch('pulse.api.team._audit_team', side_effect=frappe.ValidationError('Audit unavailable')):
            with self.assertRaises(frappe.ValidationError):
                team.invite_member(self.project.name, email, 'Failed')
        self.assertFalse(frappe.db.exists('User', email))
        self.assertNotIn(email, [r.user for r in frappe.get_doc('Project', self.project.name).users])

    def test_offboarding_preview_and_apply_handoff_and_disable(self):
        team.transfer_owner(self.project.name, self.users[0])
        from frappe.share import add
        add('Task', self.task.name, self.users[0], read=1)
        plan = team.preview_offboarding(self.users[0], self.users[1])
        self.assertEqual(len(plan['projects']), 1)
        self.assertEqual(len(plan['assignments']), 1)
        self.assertTrue(frappe.get_doc('User', self.users[0]).enabled)
        self.assertTrue(plan['shares'])
        result = team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
        self.assertTrue(result['disabled'])
        self.assertFalse(frappe.get_doc('User', self.users[0]).enabled)
        project = frappe.get_doc('Project', self.project.name)
        self.assertEqual(project.owner, self.users[1])
        self.assertNotIn(self.users[0], [r.user for r in project.users])
        self.assertTrue(frappe.db.exists('ToDo', {'reference_name': self.task.name, 'allocated_to': self.users[1], 'status': 'Open'}))
        self.assertFalse(frappe.db.exists('DocShare', {'share_doctype': 'Task', 'share_name': self.task.name, 'user': self.users[0]}))

    def test_offboarding_stale_preview_is_rejected(self):
        plan = team.preview_offboarding(self.users[0], self.users[1])
        self.task.subject = 'Changed since preview'
        self.task.save()
        # New assignment changes the reviewed scope even when there is already one task.
        frappe.get_doc({'doctype': 'ToDo', 'description': 'New work', 'allocated_to': self.users[0]}).insert()
        with self.assertRaises(frappe.ValidationError):
            team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
        self.assertTrue(frappe.get_doc('User', self.users[0]).enabled)

    def test_offboarding_failure_preserves_user_projects_and_assignments(self):
        plan = team.preview_offboarding(self.users[0], self.users[1])
        with patch('pulse.api.team._audit_team', side_effect=frappe.ValidationError('Audit unavailable')):
            with self.assertRaises(frappe.ValidationError):
                team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
        self.assertTrue(frappe.get_doc('User', self.users[0]).enabled)
        self.assertIn(self.users[0], [r.user for r in frappe.get_doc('Project', self.project.name).users])
        self.assertTrue(frappe.db.exists('ToDo', {'reference_name': self.task.name, 'allocated_to': self.users[0], 'status': 'Open'}))

    def test_project_admin_cannot_invite_or_offboard_accounts(self):
        self.assertTrue(frappe.db.exists('Role', 'Pulse Admin'))
        user = frappe.get_doc('User', self.users[1]); user.append('roles', {'role': 'Pulse Admin'}); user.save()
        frappe.set_user(self.users[1])
        self.assertFalse(team.get_team(self.project.name)['can_manage_accounts'])
        with self.assertRaises(frappe.PermissionError):
            team.invite_member(self.project.name, 'not-created@example.test', 'No')
        with self.assertRaises(frappe.PermissionError):
            team.preview_offboarding(self.users[0], self.users[1])

    def test_offboarding_protects_self_and_system_managers(self):
        with self.assertRaises(frappe.ValidationError):
            team.preview_offboarding('Administrator', self.users[1])
        user = frappe.get_doc('User', self.users[0]); user.append('roles', {'role': 'System Manager'}); user.save()
        with self.assertRaises(frappe.ValidationError):
            team.preview_offboarding(self.users[0], self.users[1])

    def test_invitation_mail_error_rolls_back_account_and_membership(self):
        email = 'mail-failure-' + frappe.generate_hash(length=8) + '@example.test'
        with patch('frappe.core.doctype.user.user.User.send_welcome_mail_to_user', side_effect=frappe.OutgoingEmailError('Configure outgoing email')):
            with self.assertRaises(frappe.OutgoingEmailError):
                team.invite_member(self.project.name, email, 'Mail failure')
        self.assertFalse(frappe.db.exists('User', email))
        self.assertNotIn(email, [r.user for r in frappe.get_doc('Project', self.project.name).users])

    def test_offboarding_schedules_session_cleanup_after_commit(self):
        plan = team.preview_offboarding(self.users[0], self.users[1])
        with patch.object(type(frappe.db.after_commit), 'add', autospec=True) as after_commit:
            team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
        cleanup = [call.args[1] for call in after_commit.call_args_list
                   if getattr(call.args[1], 'keywords', {}).get('user') == self.users[0]]
        self.assertTrue(cleanup)
        self.assertTrue(cleanup[-1].keywords['force'])

    def test_offboarding_defers_native_session_logout_until_commit(self):
        plan = team.preview_offboarding(self.users[0], self.users[1])
        manager = patch.object(frappe.local, 'login_manager', create=True)
        with manager as login_manager:
            team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
            login_manager.logout.assert_not_called()
            self.assertIs(frappe.local.login_manager, login_manager)

    def test_failed_offboarding_cannot_queue_mail_when_outer_caller_commits(self):
        from frappe.utils import CallbackManager
        from frappe.desk.form import assign_to
        postcommit_mail = Mock()
        original_add = assign_to.add
        def add_and_stage_email(*args, **kwargs):
            result = original_add(*args, **kwargs)
            frappe.db.after_commit.add(lambda: postcommit_mail(recipients=self.users[1], subject='Must not send'))
            return result
        plan = team.preview_offboarding(self.users[0], self.users[1])
        with patch.object(frappe.db, 'after_commit', CallbackManager()):
            with patch.object(assign_to, 'add', side_effect=add_and_stage_email), patch('pulse.api.team._audit_team', side_effect=frappe.ValidationError('Audit failed')):
                with self.assertRaises(frappe.ValidationError):
                    team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
            # Exactly what an outer commit does to this queue, without committing fixtures.
            frappe.db.after_commit.run()
        postcommit_mail.assert_not_called()

    def test_offboarding_revokes_external_grants_even_after_account_reenabled(self):
        grant = frappe.get_doc({'doctype': 'Pulse External Share', 'task': self.task.name,
            'user': self.users[0], 'enabled': 1}).insert(ignore_permissions=True)
        plan = team.preview_offboarding(self.users[0], self.users[1])
        self.assertEqual([row['name'] for row in plan['external_grants']], [grant.name])
        result = team.offboard_user(self.users[0], self.users[1], plan['preview_token'])
        self.assertEqual(result['external_grants_revoked'], 1)
        user = frappe.get_doc('User', self.users[0]); user.enabled = 1; user.save()
        self.assertFalse(frappe.get_doc('Pulse External Share', grant.name).enabled)

    def test_website_account_can_be_offboarded_without_becoming_system_user(self):
        email = 'external-' + frappe.generate_hash(length=8) + '@example.test'
        frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': 'External',
            'enabled': 1, 'user_type': 'Website User', 'send_welcome_email': 0}).insert()
        plan = team.preview_offboarding(email, self.users[1])
        result = team.offboard_user(email, self.users[1], plan['preview_token'])
        self.assertTrue(result['disabled'])
        self.assertEqual(frappe.get_doc('User', email).user_type, 'Website User')
