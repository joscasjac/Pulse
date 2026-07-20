"""Pulse workflow regression tests.

Covers the core PM loop and, deliberately, the bugs fixed during hardening:
issue-key collisions, subtask groups, delete-with-time, project form-meta, and
recurring tasks landing in To Do.
"""

import json

import frappe
from frappe.tests import IntegrationTestCase


class TestPulseWorkflows(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_custom_fields, ensure_default_company
        ensure_custom_fields()
        ensure_default_company()
        from pulse.api import spa
        self.project = spa.save_entity(json.dumps({
            "doctype": "Project", "project_name": "PYTEST Project", "status": "Open",
        }))["name"]

    def tearDown(self):
        for t in frappe.get_all("Task", filters={"project": self.project}, pluck="name"):
            frappe.db.set_value("Task", t, "pulse_recurring", None)
            frappe.db.set_value("Task", t, "parent_task", None)
            try:
                frappe.delete_doc("Task", t, force=True, ignore_permissions=True)
            except Exception:
                pass
        for r in frappe.get_all("Pulse Recurring Task", filters={"project": self.project}, pluck="name"):
            frappe.delete_doc("Pulse Recurring Task", r, force=True, ignore_permissions=True)
        if frappe.db.exists("Project", self.project):
            frappe.delete_doc("Project", self.project, force=True, ignore_permissions=True)
        frappe.db.commit()

    # --- core CRUD ---
    def test_create_task_gets_issue_key_and_state(self):
        from pulse.api import spa
        t = spa.create_task(project=self.project, subject="crud", state="To Do")
        self.assertTrue(t["issue_key"])
        self.assertEqual(frappe.db.get_value("Task", t["name"], "workflow_state"), "To Do")

    def test_update_and_move_state(self):
        from pulse.api import spa
        t = spa.create_task(project=self.project, subject="move", state="Backlog")
        spa.update_task(t["name"], priority="High", pulse_story_points=5)
        spa.update_task_state(t["name"], "In Progress")
        v = frappe.db.get_value("Task", t["name"], ["priority", "workflow_state"], as_dict=True)
        self.assertEqual(v.priority, "High")
        self.assertEqual(v.workflow_state, "In Progress")

    def test_board_comment_checklist(self):
        from pulse.api import spa
        t = spa.create_task(project=self.project, subject="board", state="Backlog")
        self.assertTrue(spa.get_board(project=self.project))
        self.assertTrue(spa.add_comment(t["name"], "hi"))
        self.assertTrue(spa.add_checklist_item(t["name"], "item"))

    # --- regression: subtask must promote parent to a group ---
    def test_subtask_promotes_parent_group(self):
        from pulse.api import spa
        t = spa.create_task(project=self.project, subject="parent", state="To Do")
        spa.add_subtask(t["name"], "child")
        self.assertEqual(frappe.db.get_value("Task", t["name"], "is_group"), 1)

    # --- regression: deleting a task that has logged time must succeed ---
    def test_delete_task_with_logged_time(self):
        from pulse.api import spa
        from pulse.api import time as timeapi
        t = spa.create_task(project=self.project, subject="timed", state="To Do")
        timeapi.log_time(t["name"], 1.5, note="x")
        self.assertGreaterEqual(timeapi.get_task_time(t["name"]), 1.5)
        spa.delete_task(t["name"])
        self.assertFalse(frappe.db.exists("Task", t["name"]))

    # --- regression: issue keys never collide, even after deletions ---
    def test_issue_keys_unique_after_deletion(self):
        from pulse.api import spa
        a = spa.create_task(project=self.project, subject="a", state="To Do")
        spa.delete_task(a["name"])  # counter does not roll back
        b = spa.create_task(project=self.project, subject="b", state="To Do")
        c = spa.create_task(project=self.project, subject="c", state="To Do")
        self.assertNotEqual(b["issue_key"], c["issue_key"])

    # --- regression: New Project form meta returns curated fields ---
    def test_project_form_meta_curated(self):
        from pulse.api import spa
        fns = [f["fieldname"] for f in spa.get_form_meta("Project")["fields"]]
        self.assertIn("project_name", fns)
        self.assertLessEqual(len(fns), 10)

    # --- recurring: generates a task into To Do and advances next_run ---
    def test_recurring_generates_into_todo(self):
        from pulse.api import recurring
        r = recurring.create_recurring(subject="weekly", project=self.project,
                                       interval_count=1, interval_unit="Week", generate_now=1)
        self.assertEqual(len(r["generated"]), 1)
        gt = frappe.get_all("Task", filters={"pulse_recurring": r["name"]},
                            fields=["workflow_state"])
        self.assertEqual(gt[0]["workflow_state"], "To Do")
        self.assertGreater(str(r["next_run"]), frappe.utils.today())

    # --- modules are real editable doctypes ---
    def test_module_doctypes_editable(self):
        from pulse.api import spa
        for dt in ("Pulse Objective", "Pulse Risk", "Pulse Meeting"):
            self.assertTrue(spa.get_form_meta(dt)["fields"])
