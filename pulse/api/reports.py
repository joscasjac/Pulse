"""Pulse reports exposed to the SPA (canonical namespace: pulse.api.reports.*).

The agile reports live as Frappe report modules; these endpoints run them and
hand the SPA real columns/rows so the reports are reachable from Pulse itself
rather than only from the Desk.
"""

import frappe
from frappe import _

REPORTS = {
    "burndown": {
        "label": "Sprint Burndown",
        "module": "pulse.pulse.report.pulse_burndown.pulse_burndown",
        "needs_sprint": True,
        "chart": {"x": "date", "series": ["ideal_remaining", "actual_remaining"]},
    },
    "burnup": {
        "label": "Sprint Burnup",
        "module": "pulse.pulse.report.pulse_burnup.pulse_burnup",
        "needs_sprint": True,
        "chart": {"x": "date", "series": ["scope", "completed"]},
    },
    "sprint": {
        "label": "Sprint Report",
        "module": "pulse.pulse.report.pulse_sprint_report.pulse_sprint_report",
        "needs_sprint": True,
        "chart": None,
    },
    "workload": {
        "label": "Workload by Assignee",
        "module": "pulse.pulse.report.pulse_workload.pulse_workload",
        "needs_sprint": False,
        "chart": None,
    },
}


@frappe.whitelist()
def list_reports():
    return [
        {"key": k, "label": v["label"], "needs_sprint": v["needs_sprint"],
         "chart": v["chart"]}
        for k, v in REPORTS.items()
    ]


@frappe.whitelist()
def sprint_options(project=None):
    filters = {}
    if project:
        filters["project"] = project
    return frappe.get_list(
        "Pulse Sprint", filters=filters,
        fields=["name", "sprint_name", "status", "project"],
        order_by="start_date desc", limit_page_length=0,
    )


@frappe.whitelist()
def run_report(report, project=None, sprint=None):
    cfg = REPORTS.get(report)
    if not cfg:
        frappe.throw(_("Unknown report: {0}").format(report))
    mod = frappe.get_module(cfg["module"])
    try:
        columns, data = mod.execute({"project": project, "sprint": sprint})
    except Exception:
        frappe.log_error(title="Pulse: report failed", message=frappe.get_traceback())
        frappe.throw(_("This report could not be generated."))
    return {
        "key": report,
        "label": cfg["label"],
        "chart": cfg["chart"],
        "columns": columns or [],
        "data": data or [],
    }


def sprint_history_report(filters=None):
    """Historical chart data starts at the first actual observation, never backfilled."""
    from pulse.api.planning import _sprint
    from pulse.api.sprint_history import read_events
    from pulse.utils.sprint_metrics import replay
    from frappe.utils import getdate
    filters = filters or {}
    name = filters.get("sprint")
    if not name and filters.get("project"):
        candidates = frappe.get_list("Pulse Sprint", filters={"project": filters['project'], "status": "Active"}, pluck="name")
        name = candidates[0] if candidates else None
    if not name:
        return [], []
    sprint = _sprint(name)
    if not sprint.get("history_started_at"):
        frappe.throw("Historical data is unavailable for this sprint; no baseline was recorded.")
    if not sprint.start_date or not sprint.end_date:
        return [], []
    start = max(getdate(sprint.start_date), getdate(sprint.history_started_at))
    end = min(getdate(sprint.end_date), getdate(sprint.closed_at)) if sprint.get('closed_at') else getdate(sprint.end_date)
    events = read_events(sprint)
    measure = sprint.get('progress_measure') or 'Tasks'
    baseline_scope = sum(1 if measure == 'Tasks' else float(e['state'].get(measure.lower(), 0) or 0)
                         for e in events if e['kind'] == 'Baseline' and e['state']['present'])
    data = replay(events, start, end, measure, today=getdate(),
                  baseline_scope=baseline_scope, ideal_end=sprint.end_date)
    columns = [{"label": label, "fieldname": name, "fieldtype": kind, "width": 145}
               for name, label, kind in [("date", "Date", "Date"), ("scope", "Scope", "Float"),
                                        ("completed", "Completed", "Float"),
                                        ("ideal_remaining", "Ideal Remaining", "Float"),
                                        ("actual_remaining", "Actual Remaining", "Float")]]
    return columns, data
