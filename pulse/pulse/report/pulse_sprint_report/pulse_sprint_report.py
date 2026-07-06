import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
    filters = filters or {}
    sprint_name = filters.get("sprint")
    if not sprint_name:
        return [], []

    sprint = frappe.get_doc("Pulse Sprint", sprint_name)
    start = getdate(sprint.start_date) if sprint.start_date else None
    end = getdate(sprint.end_date) if sprint.end_date else None

    planned = float(sprint.planned_points or 0)
    completed_points = float(sprint.completed_points or 0)

    tasks = frappe.get_all(
        "Pulse Task",
        filters={"pulse_sprint": sprint_name},
        fields=[
            "name",
            "subject",
            "pulse_story_points",
            "workflow_state",
            "status",
            "type",
            "creation",
        ],
        order_by="pulse_rank asc",
    )

    log_rows = frappe.get_all(
        "Pulse Task Status Log",
        filters={"sprint": sprint_name},
        fields=["task", "to_state", "changed_on", "points_at_change"],
        order_by="changed_on asc",
    )

    task_log = {}
    for r in log_rows:
        rd = getdate(r.changed_on)
        if r.task not in task_log or rd < task_log[r.task]["first_date"]:
            task_log.setdefault(r.task, {})["first_date"] = rd
        if r.to_state == "Done" and (
            r.task not in task_log
            or "done_date" not in task_log[r.task]
            or rd < task_log[r.task].get("done_date")
        ):
            task_log.setdefault(r.task, {})["done_date"] = rd

    added_points = 0
    removed_points = 0
    spillover = 0
    spillover_count = 0
    completed = 0
    detail = []

    for t in tasks:
        pts = float(t.pulse_story_points or 0)
        info = task_log.get(t.name, {})
        entered_on = info.get("first_date", getdate(t.creation))

        if entered_on > start:
            added_points += pts

        is_done_by_log = "done_date" in info and info["done_date"] <= end
        is_done_live = t.workflow_state == "Done" or t.status == "Completed"

        if is_done_by_log:
            outcome = _("Completed")
            completed += pts
        elif not is_done_live and t.pulse_sprint == sprint_name:
            outcome = _("Spillover")
            spillover += pts
            spillover_count += 1
        else:
            outcome = _("Removed")
            removed_points += pts

        detail.append(
            {
                "task": t.name,
                "subject": t.subject,
                "type": t.type,
                "points": pts,
                "entered_on": entered_on,
                "state": t.workflow_state,
                "outcome": outcome,
            }
        )

    complete_pct = round(100 * completed_points / planned, 1) if planned else 0

    summary = [
        {"label": _("Planned Points"), "value": planned},
        {"label": _("Completed Points"), "value": completed_points},
        {"label": _("Completed %"), "value": complete_pct},
        {"label": _("Added Points"), "value": added_points},
        {"label": _("Removed Points"), "value": removed_points},
        {"label": _("Spillover Points"), "value": spillover},
        {"label": _("Spillover Tasks"), "value": spillover_count},
    ]

    return get_columns(), get_data(summary, detail)


def get_columns():
    return [
        {
            "label": _("Section"),
            "fieldname": "section",
            "fieldtype": "Data",
            "width": 200,
        },
        {"label": _("Value"), "fieldname": "value", "fieldtype": "Data", "width": 150},
        {
            "label": _("Task"),
            "fieldname": "task",
            "fieldtype": "Link",
            "options": "Pulse Task",
            "width": 120,
        },
        {
            "label": _("Subject"),
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 250,
        },
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 100},
        {
            "label": _("Points"),
            "fieldname": "points",
            "fieldtype": "Float",
            "width": 80,
        },
        {
            "label": _("Entered Sprint On"),
            "fieldname": "entered_on",
            "fieldtype": "Date",
            "width": 140,
        },
        {"label": _("State"), "fieldname": "state", "fieldtype": "Data", "width": 100},
        {
            "label": _("Outcome"),
            "fieldname": "outcome",
            "fieldtype": "Data",
            "width": 100,
        },
    ]


def get_data(summary, detail):
    data = []
    data.append({"section": "<b>" + _("Summary") + "</b>", "value": ""})
    for s in summary:
        data.append({"section": s["label"], "value": s["value"]})
    data.append({"section": "", "value": ""})
    data.append({"section": "<b>" + _("Tasks") + "</b>", "value": ""})
    for d in detail:
        data.append(
            {
                "task": d["task"],
                "subject": d["subject"],
                "type": d["type"],
                "points": d["points"],
                "entered_on": d.get("entered_on", ""),
                "state": d["state"],
                "outcome": d["outcome"],
            }
        )
    return data
