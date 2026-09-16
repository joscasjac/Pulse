"""Run with bench --site SITE run-tests --app pulse --module pulse.tests.test_sprint_planning."""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today, add_days


class TestSprintPlanning(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_default_company
        ensure_default_company()
        from pulse.api.spa import save_entity
        self.project = save_entity(frappe.as_json({"doctype": "Project", "project_name": "Sprint integration " + frappe.generate_hash(length=8), "status": "Open"}))["name"]
        self.sprint = frappe.get_doc({"doctype": "Pulse Sprint", "project": self.project,
                                      "sprint_name": "History test", "start_date": today(),
                                      "end_date": add_days(today(), 5)}).insert()

    def test_baseline_reopening_and_close_disposition(self):
        from pulse.api.spa import create_task, update_task_state
        from pulse.api.planning import move_to_sprint, close_sprint
        from pulse.api.sprint_history import read_events
        task = create_task(project=self.project, subject="Sprint task", state="To Do")
        move_to_sprint([task['name']], self.sprint.name)
        self.sprint.status = "Active"
        self.sprint.save()
        self.assertTrue(self.sprint.history_started_at)
        update_task_state(task['name'], "Done")
        update_task_state(task['name'], "In Progress")
        events = read_events(self.sprint)
        self.assertTrue(any(e['state']['completed'] for e in events))
        self.assertFalse(events[-1]['state']['completed'])
        summary = close_sprint(self.sprint.name, unfinished="backlog")
        self.assertEqual(summary['unfinished_task_ids'], [task['name']])
        self.assertFalse(frappe.db.get_value("Task", task['name'], "pulse_sprint"))
        self.assertEqual(frappe.db.get_value("Pulse Sprint", self.sprint.name, "status"), "Completed")

    def test_direct_close_requires_disposition(self):
        self.sprint.status = "Completed"
        with self.assertRaises(frappe.ValidationError):
            self.sprint.save()

    def test_active_sprint_cannot_return_to_planned(self):
        self.sprint.status = "Active"
        self.sprint.save()
        self.sprint.status = "Planned"
        with self.assertRaises(frappe.ValidationError):
            self.sprint.save()

    def test_closed_dates_and_goal_are_frozen(self):
        from pulse.api.planning import close_sprint
        self.sprint.status = "Active"
        self.sprint.save()
        close_sprint(self.sprint.name, unfinished="retain")
        for field, value in [("end_date", add_days(today(), 10)), ("goal", "Changed goal")]:
            closed = frappe.get_doc("Pulse Sprint", self.sprint.name)
            closed.set(field, value)
            with self.assertRaises(frappe.ValidationError):
                closed.save()

    def test_empty_sprint_still_validates_carryover_destination(self):
        from pulse.api.planning import close_sprint
        self.sprint.status = "Active"
        self.sprint.save()
        with self.assertRaises(frappe.DoesNotExistError):
            close_sprint(self.sprint.name, unfinished="next", next_sprint="missing-sprint")
        self.assertEqual(frappe.db.get_value("Pulse Sprint", self.sprint.name, "status"), "Active")

    def test_next_sprint_and_frozen_effort_summary(self):
        from pulse.api.spa import create_task, update_task_state
        from pulse.api.planning import move_to_sprint, close_sprint, sprint_progress
        tasks = [create_task(project=self.project, subject=label, state="To Do") for label in ("Done work", "Carryover work")]
        for task, hours, points in zip(tasks, (3, 5), (2, 3)):
            doc = frappe.get_doc("Task", task['name'])
            doc.expected_time, doc.pulse_story_points = hours, points
            doc.save()
        move_to_sprint([t['name'] for t in tasks], self.sprint.name)
        self.sprint.status, self.sprint.progress_measure = "Active", "Hours"
        self.sprint.save()
        update_task_state(tasks[0]['name'], "Done")
        destination = frappe.get_doc({"doctype": "Pulse Sprint", "project": self.project,
                                      "sprint_name": "Next cycle"}).insert()
        summary = close_sprint(self.sprint.name, unfinished="next", next_sprint=destination.name)
        self.assertEqual((summary['planned'], summary['completed']), (8, 3))
        self.assertEqual(frappe.db.get_value("Task", tasks[1]['name'], "pulse_sprint"), destination.name)
        update_task_state(tasks[1]['name'], "Done")
        self.assertEqual(sprint_progress(self.sprint.name), summary)

    def test_recorded_history_start_cannot_be_cleared(self):
        self.sprint.status = "Active"
        self.sprint.save()
        self.sprint.history_started_at = None
        with self.assertRaises(frappe.ValidationError):
            self.sprint.save()

    def _member(self, role="Pulse Manager"):
        user = "sprint-" + frappe.generate_hash(length=8) + "@example.com"
        frappe.get_doc({"doctype": "User", "email": user, "first_name": "Sprint member",
                        "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
        project = frappe.get_doc("Project", self.project)
        project.append("users", {"user": user, "welcome_email_sent": 1})
        project.save()
        return user

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_native_task_save_requires_sprint_write(self):
        user = self._member("Pulse Senior Developer")
        task = frappe.get_doc({"doctype": "Task", "subject": "Native planning permission",
                               "project": self.project}).insert()
        frappe.set_user(user)
        self.assertTrue(frappe.has_permission("Task", "write", doc=task))
        task.pulse_sprint = self.sprint.name
        with self.assertRaises(frappe.PermissionError):
            task.save()

    def test_archive_records_scope_and_excludes_closure_work(self):
        from pulse.api.planning import sprint_progress, close_sprint
        from pulse.api.sprint_history import read_events
        task = frappe.get_doc({"doctype": "Task", "subject": "Archive sprint scope",
                               "project": self.project, "pulse_sprint": self.sprint.name,
                               "expected_time": 5}).insert()
        self.sprint.status = "Active"
        self.sprint.save()
        task.pulse_archived = 1
        task.save()
        self.assertEqual(sprint_progress(self.sprint.name)['tasks'], 0)
        self.assertEqual(frappe.db.get_value("Pulse Sprint", self.sprint.name, "planned_tasks"), 0)
        self.assertEqual(read_events(self.sprint)[-1]['kind'], "Removed")
        task.pulse_archived = 0
        task.save()
        self.assertEqual(read_events(self.sprint)[-1]['kind'], "Added")
        task.pulse_archived = 1
        task.save()
        summary = close_sprint(self.sprint.name, unfinished="backlog")
        self.assertEqual(summary['estimated_hours'], 0)
        self.assertEqual(summary['unfinished_task_ids'], [])
        self.assertEqual(frappe.db.get_value("Task", task.name, "pulse_sprint"), self.sprint.name)

    def test_close_moves_more_than_200_tasks_atomically(self):
        from pulse.api.planning import close_sprint
        for index in range(201):
            frappe.get_doc({"doctype": "Task", "subject": f"Large sprint {index}",
                            "project": self.project, "pulse_sprint": self.sprint.name}).insert()
        self.sprint.status = "Active"
        self.sprint.save()
        summary = close_sprint(self.sprint.name, unfinished="backlog")
        self.assertEqual(len(summary['unfinished_task_ids']), 201)
        self.assertEqual(frappe.db.count("Task", {"pulse_sprint": self.sprint.name}), 0)
        self.assertEqual(frappe.db.get_value("Pulse Sprint", self.sprint.name, "status"), "Completed")

    def test_deleted_history_readable_to_manager_and_closable(self):
        from pulse.api.planning import close_sprint, sprint_progress
        from pulse.api.sprint_history import read_events
        user = self._member()
        task = frappe.get_doc({"doctype": "Task", "subject": "Deleted scope",
                               "project": self.project, "pulse_sprint": self.sprint.name}).insert()
        self.sprint.status = "Active"
        self.sprint.save()
        frappe.delete_doc("Task", task.name, force=1)
        frappe.set_user(user)
        self.assertEqual(read_events(self.sprint)[-1]['kind'], "Deleted")
        summary = close_sprint(self.sprint.name, unfinished="retain")
        self.assertIn(task.name, summary['scope_removed'])
        self.assertEqual(sprint_progress(self.sprint.name), summary)

    def test_deleted_history_does_not_reveal_unassigned_work(self):
        from pulse.api.sprint_history import read_events
        user = self._member("Pulse Junior Developer")
        task = frappe.get_doc({"doctype": "Task", "subject": "Private deleted scope",
                               "project": self.project, "pulse_sprint": self.sprint.name}).insert()
        self.sprint.status = "Active"
        self.sprint.save()
        frappe.delete_doc("Task", task.name, force=1)
        frappe.set_user(user)
        with self.assertRaises(frappe.PermissionError):
            read_events(self.sprint)

    def test_deleted_history_does_not_allow_hidden_surviving_tasks(self):
        from pulse.api.sprint_history import read_events
        user = self._member("Pulse Junior Developer")
        tasks = [frappe.get_doc({"doctype": "Task", "subject": label, "project": self.project,
                                "pulse_sprint": self.sprint.name}).insert()
                 for label in ("Deleted assigned scope", "Private surviving scope")]
        frappe.db.set_value("Task", tasks[0].name, "_assign", frappe.as_json([user]))
        self.sprint.status = "Active"
        self.sprint.save()
        frappe.delete_doc("Task", tasks[0].name, force=1)
        frappe.set_user(user)
        with self.assertRaises(frappe.PermissionError):
            read_events(self.sprint)
