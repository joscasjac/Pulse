"""Velocity from permission-checked frozen sprint outcomes."""
import frappe
from pulse.hooks.permissions import require_permission
from pulse.api.planning import sprint_progress


def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")
    if project:
        require_permission("Project", project)
    scope = {"status": "Completed"}
    if project:
        scope["project"] = project
    limit = max(1, min(int(filters.get("last_n_sprints") or 6), 100))
    sprints = frappe.get_list("Pulse Sprint", filters=scope,
                              fields=["name", "start_date", "end_date"],
                              order_by="end_date desc", limit_page_length=limit)
    data = []
    for sprint in sprints:
        doc = require_permission("Pulse Sprint", sprint.name)
        if not doc.get("closure_summary"):
            frappe.throw("Historical velocity is unavailable for a sprint without a recorded closure outcome.")
        summary = sprint_progress(sprint.name)
        data.append({"sprint": sprint.name, "start_date": sprint.start_date,
                     "end_date": sprint.end_date, "measure": summary["measure"],
                     "planned": summary["planned"], "completed": summary["completed"],
                     "velocity": summary["completed"], "attainment": summary["percent"]})
    columns = [{"fieldname": name, "label": label, "fieldtype": kind, "width": 140}
               for name, label, kind in [("sprint", "Sprint", "Data"), ("start_date", "Start Date", "Date"),
                                         ("end_date", "End Date", "Date"), ("measure", "Measure", "Data"),
                                         ("planned", "Planned", "Float"), ("completed", "Completed", "Float"),
                                         ("velocity", "Velocity", "Float"), ("attainment", "Attainment %", "Percent")]]
    return columns, data
