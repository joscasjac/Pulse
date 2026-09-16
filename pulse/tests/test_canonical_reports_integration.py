"""Native reports must not expose another project's task counts or cached stats."""
import frappe
from frappe.tests import IntegrationTestCase


class TestCanonicalReports(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        suffix = frappe.generate_hash(length=8)
        self.user = f"pulse-report-{suffix}@example.com"
        frappe.get_doc({"doctype": "User", "email": self.user, "first_name": "Report Test",
                        "send_welcome_email": 0, "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        self.visible = frappe.get_doc({"doctype": "Project", "project_name": "Report visible " + suffix,
                                      "users": [{"user": self.user, "welcome_email_sent": 1}]}).insert()
        self.hidden = frappe.get_doc({"doctype": "Project", "project_name": "Report hidden " + suffix}).insert()
        from pulse.api.task_config import save_config
        save_config(self.visible.name, [{"label": "Client waiting", "category": "Blocked", "color": "#ff0000"},
                                       {"label": "Reviewing", "category": "In Review", "color": "#0000ff"}], [])
        for project, state in [(self.visible.name, "Client waiting"), (self.visible.name, "Reviewing"),
                               (self.hidden.name, "To Do")]:
            frappe.get_doc({"doctype": "Task", "subject": "Report scoped task", "project": project,
                            "workflow_state": state}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_native_categories_and_permission_scope(self):
        from pulse.pulse.report.status_of_issues_across_projects.status_of_issues_across_projects import execute
        frappe.set_user(self.user)
        _, rows = execute()
        by_project = {row["project"]: row for row in rows}
        self.assertNotIn(self.hidden.name, by_project)
        self.assertEqual(by_project[self.visible.name]["blocked"], 1)
        self.assertEqual(by_project[self.visible.name]["in_review"], 1)
        self.assertEqual(by_project[self.visible.name]["total"], 2)

    def test_helper_checks_permission_before_returning_stats(self):
        from pulse.utils.helpers import get_cached_project_stats, get_project_key
        self.assertEqual(get_cached_project_stats(self.hidden.name)["total_tasks"], 1)
        frappe.set_user(self.user)
        with self.assertRaises(frappe.PermissionError):
            get_cached_project_stats(self.hidden.name)
        with self.assertRaises(frappe.PermissionError):
            get_project_key(self.hidden.name)
        self.assertEqual(get_cached_project_stats(self.visible.name)["total_tasks"], 2)

    def test_empty_reports_never_fabricate_demo_data(self):
        from unittest.mock import patch
        from pulse.pulse.report.issues_in_active_sprints.issues_in_active_sprints import execute as sprint_report
        from pulse.pulse.report.average_time_spent_on_work.average_time_spent_on_work import execute as time_report
        with patch("frappe.get_list", return_value=[]):
            self.assertEqual(sprint_report()[1], [])
            self.assertEqual(time_report()[1], [])

    def test_time_report_filters_projects_and_submitted_entries(self):
        from unittest.mock import patch
        from pulse.pulse.report.average_time_spent_on_work import average_time_spent_on_work as report
        rows = [{"project": self.visible.name, "hours": 2, "docstatus": 1},
                {"project": self.visible.name, "hours": 6, "docstatus": 1},
                {"project": self.visible.name, "hours": 20, "docstatus": 0},
                {"project": self.hidden.name, "hours": 100, "docstatus": 1}]
        frappe.set_user(self.user)
        with patch.object(report, "_entries", return_value=rows):
            self.assertEqual(report.execute()[1], [{"project": self.visible.name, "average_hours": 4, "entries": 2}])

    def test_active_sprint_counts_visible_native_tasks(self):
        from pulse.pulse.report.issues_in_active_sprints.issues_in_active_sprints import execute
        names = []
        for project in (self.visible, self.hidden):
            sprint = frappe.get_doc({"doctype": "Pulse Sprint", "sprint_name": "Report " + project.name,
                                     "project": project.name, "status": "Active",
                                     "start_date": frappe.utils.today(), "end_date": frappe.utils.add_days(frappe.utils.today(), 7)}).insert()
            names.append(sprint.sprint_name)
            for task in frappe.get_all("Task", filters={"project": project.name}, pluck="name"):
                doc = frappe.get_doc("Task", task)
                doc.pulse_sprint = sprint.name
                doc.save()
        frappe.set_user(self.user)
        rows = {row["sprint"]: row for row in execute()[1]}
        self.assertNotIn(names[1], rows)
        self.assertEqual(rows[names[0]]["issues"], 2)
        self.assertEqual(rows[names[0]]["percentage"], 100)
