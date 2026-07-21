"""Keep agile metrics fresh.

Burndown/CFD/cycle-time are derived on demand from Pulse Task Status Log, so no
snapshot table is required. This job refreshes the rolled-up TASK COUNTS on
active sprints so dashboards stay current even if a Task was edited via SQL or
an import that skipped doc-events.
"""

import frappe


def snapshot_burndown():
    active = frappe.get_all("Pulse Sprint", filters={"status": "Active"}, pluck="name")
    if not active:
        return
    rows = frappe.get_all(
        "Task",
        filters={"pulse_sprint": ["in", active]},
        fields=["pulse_sprint", "status", "workflow_state"],
    )
    planned = {}
    completed = {}
    for r in rows:
        sprint = r.pulse_sprint
        planned[sprint] = planned.get(sprint, 0) + 1
        completed.setdefault(sprint, 0)
        if r.workflow_state == "Done" or r.status == "Completed":
            completed[sprint] += 1
    for name in active:
        try:
            sprint_doc = frappe.get_doc("Pulse Sprint", name)
            sprint_doc.db_set("planned_tasks", planned.get(name, 0), update_modified=False)
            sprint_doc.db_set("completed_tasks", completed.get(name, 0), update_modified=False)
        except Exception:
            frappe.log_error(
                title="Pulse: metric refresh failed", message=frappe.get_traceback()
            )
