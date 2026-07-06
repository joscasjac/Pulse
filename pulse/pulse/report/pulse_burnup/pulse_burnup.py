import frappe
from frappe import _
from frappe.utils import getdate, add_days


def execute(filters=None):
    filters = filters or {}
    sprint_name = filters.get("sprint")
    if not sprint_name:
        return [], []

    sprint = frappe.get_doc("Pulse Sprint", sprint_name)
    if not sprint.start_date or not sprint.end_date:
        return [], []

    from_date = getdate(sprint.start_date)
    to_date = getdate(sprint.end_date)

    log_rows = frappe.get_all(
        "Pulse Task Status Log",
        filters={"sprint": sprint_name},
        fields=["task", "to_state", "changed_on", "points_at_change"],
        order_by="changed_on asc",
    )

    tasks_in_sprint = {r.task for r in log_rows}
    current_sprints = dict(
        frappe.db.sql(
            "SELECT name, pulse_sprint FROM `tabPulse Task` WHERE name IN (%s)"
            % ",".join(frappe.db.escape(t) for t in tasks_in_sprint)
        )
    )

    task_removed_on = {}
    task_first_entry = {}
    for r in log_rows:
        rd = getdate(r.changed_on)
        if r.task not in task_first_entry:
            task_first_entry[r.task] = rd
        task_removed_on[r.task] = rd

    columns = [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
        {
            "label": _("Scope"),
            "fieldname": "scope",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": _("Completed"),
            "fieldname": "completed",
            "fieldtype": "Float",
            "width": 140,
        },
    ]

    data = []
    num_days = (to_date - from_date).days or 1

    for i in range(num_days + 1):
        day = add_days(from_date, i)
        if day > to_date:
            day = to_date

        task_latest = {}
        for r in log_rows:
            rd = getdate(r.changed_on)
            if rd <= day:
                task_latest[r.task] = {
                    "points": flt(r.points_at_change),
                    "state": r.to_state,
                }

        scope = 0
        completed = 0
        for task, info in task_latest.items():
            current_sprint = current_sprints.get(task)
            removed = (
                current_sprint != sprint_name
                and task_removed_on.get(task, to_date) <= day
            )
            entered = task_first_entry.get(task, from_date) <= day
            if entered and not removed:
                scope += info["points"]
                if info["state"] == "Done":
                    completed += info["points"]

        data.append(
            {
                "date": day,
                "scope": round(scope, 1),
                "completed": round(completed, 1),
            }
        )
        if day >= to_date:
            break

    return columns, data


def flt(v):
    return float(v or 0)
