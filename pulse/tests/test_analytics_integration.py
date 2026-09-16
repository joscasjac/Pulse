"""Scope and semantic-status regressions exercised against native Task records."""
import frappe
from frappe.tests import IntegrationTestCase


class TestAnalyticsIntegration(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.projects = [frappe.get_doc({"doctype": "Project", "project_name": "Analytics " + label + " " + frappe.generate_hash(length=8)}).insert()
                         for label in ("Selected", "Other")]

    def tearDown(self):
        for project in self.projects:
            for name in frappe.get_all("Task", filters={"project": project.name}, pluck="name"):
                from pulse.api.spa import delete_task
                delete_task(name)
            frappe.delete_doc("Project", project.name, force=True)

    def test_every_series_respects_selected_project(self):
        from pulse.api.spa import create_task
        from pulse.api.analytics import get_analytics
        create_task(self.projects[0].name, "Selected review", state="In Review")
        create_task(self.projects[1].name, "Other done", state="Done")
        selected = get_analytics(self.projects[0].name)
        self.assertEqual(selected["completion"]["estimated"], 1)
        self.assertEqual(selected["kpis"]["completed"], 0)
        self.assertEqual(selected["kpis"]["blocked"], 0)
        self.assertEqual(selected["status_distribution"], [{"label": "Pending Review", "value": 1}])

    def test_custom_blocked_category_and_archive(self):
        from pulse.api.task_config import save_config
        from pulse.api.spa import create_task
        from pulse.api.tasks import bulk_update
        from pulse.api.analytics import get_analytics
        project = self.projects[0].name
        save_config(project, [
            {"label": "Waiting for client", "color": "#aa5500", "category": "Blocked"},
            {"label": "Finished", "color": "#00aa55", "category": "Done"},
        ], [])
        task = create_task(project, "Awaiting approval", state="Waiting for client")
        self.assertEqual(get_analytics(project)["kpis"]["blocked"], 1)
        bulk_update([task["name"]], {"pulse_archived": 1})
        self.assertEqual(get_analytics(project)["completion"]["estimated"], 0)
