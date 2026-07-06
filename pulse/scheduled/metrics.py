"""Keep agile metrics fresh.

Burndown/CFD/cycle-time are derived on demand from Pulse Task Status Log, so no
snapshot table is required. This job simply refreshes the rolled-up point totals
on active sprints so dashboards stay current even if a Task was edited via SQL
or an import that skipped doc-events.
"""

import frappe
from frappe.utils import flt


def snapshot_burndown():
    active = frappe.get_all("Pulse Sprint", filters={"status": "Active"}, pluck="name")
    if not active:
        return
    rows = frappe.get_all(
        "Pulse Task",
        filters={"pulse_sprint": ["in", active]},
        fields=["pulse_sprint", "pulse_story_points", "status", "workflow_state"],
    )
    planned = {}
    completed = {}
    for r in rows:
        sprint = r.pulse_sprint
        planned.setdefault(sprint, 0)
        completed.setdefault(sprint, 0)
        pts = flt(r.pulse_story_points)
        planned[sprint] += pts
        if r.workflow_state == "Done" or r.status == "Completed":
            completed[sprint] += pts
    for name in active:
        try:
            sprint_doc = frappe.get_doc("Pulse Sprint", name)
            sprint_doc.db_set(
                "planned_points", planned.get(name, 0), update_modified=False
            )
            sprint_doc.db_set(
                "completed_points", completed.get(name, 0), update_modified=False
            )
        except Exception:
            frappe.log_error(
                title="Pulse: metric refresh failed", message=frappe.get_traceback()
            )
