import frappe
from frappe import _
from frappe.utils import getdate, add_days


def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")
    sprint = filters.get("sprint")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    task_type = filters.get("task_type")
    assignee = filters.get("assignee")

    if not project:
        return [], []

    from pulse.hooks.permissions import require_permission
    require_permission("Project", project)
    visible = frappe.get_list("Task", filters={"project": project}, pluck="name", limit_page_length=0)
    if not visible:
        return [], []
    conditions = ["t.project = %(project)s", "t.name IN %(visible)s"]
    if sprint:
        conditions.append("t.pulse_sprint = %(sprint)s")
    if from_date:
        conditions.append("dn.done_on >= %(from_date)s")
    if to_date:
        conditions.append("dn.done_on <= %(to_date)s")
    if task_type:
        conditions.append("t.type = %(task_type)s")
    if assignee:
        conditions.append("t._assign like %(assignee)s")

    data = frappe.db.sql(
        f"""
        SELECT
            ip.task,
            t.subject,
            t.type AS type,
            ip.started_on,
            dn.done_on,
            t.project,
            TIMESTAMPDIFF(HOUR, ip.started_on, dn.done_on) / 24.0 AS cycle_days
        FROM (
            SELECT task, MIN(changed_on) AS started_on
            FROM `tabPulse Task Status Log`
            WHERE to_state = 'In Progress' AND project = %(project)s
            GROUP BY task
        ) ip
        JOIN (
            SELECT task, MIN(changed_on) AS done_on
            FROM `tabPulse Task Status Log`
            WHERE to_state = 'Done' AND project = %(project)s
            GROUP BY task
        ) dn ON dn.task = ip.task
        JOIN `tabTask` t ON t.name = ip.task
        WHERE ip.started_on < dn.done_on
        AND {" AND ".join(conditions)}
        ORDER BY dn.done_on DESC
        """,
        {
            "project": project,
            "visible": tuple(visible),
            "sprint": sprint,
            "from_date": from_date,
            "to_date": to_date,
            "task_type": task_type,
            "assignee": f"%{assignee}%" if assignee else None,
        },
        as_dict=True,
    )

    holiday_list = get_holiday_list(project)
    for row in data:
        row["cycle_working_days"] = count_working_days(
            getdate(row.started_on), getdate(row.done_on), holiday_list
        )

    days_vals = [r["cycle_days"] for r in data if r["cycle_days"] is not None]
    working_vals = [
        r["cycle_working_days"] for r in data if r["cycle_working_days"] is not None
    ]

    columns = [
        {
            "label": _("Task"),
            "fieldname": "task",
            "fieldtype": "Link",
            "options": "Task",
            "width": 150,
        },
        {
            "label": _("Subject"),
            "fieldname": "subject",
            "fieldtype": "Data",
            "width": 250,
        },
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 100},
        {
            "label": _("Started On"),
            "fieldname": "started_on",
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "label": _("Done On"),
            "fieldname": "done_on",
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "label": _("Cycle Time (days)"),
            "fieldname": "cycle_days",
            "fieldtype": "Float",
            "width": 140,
            "precision": 1,
        },
        {
            "label": _("Cycle Time (working days)"),
            "fieldname": "cycle_working_days",
            "fieldtype": "Float",
            "width": 170,
            "precision": 1,
        },
    ]

    return columns, data


def get_holiday_list(project):
    holiday_list = frappe.db.get_value("Project", project, "holiday_list")
    if not holiday_list:
        holiday_list = frappe.db.get_single_value(
            "Pulse Settings", "working_days_source"
        )
    return holiday_list


def count_working_days(start_date, end_date, holiday_list=None):
    if start_date > end_date:
        return 0
    holidays = set()
    if holiday_list:
        holidays = set(
            frappe.get_all(
                "Holiday", filters={"parent": holiday_list}, pluck="holiday_date"
            )
        )
    days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current = add_days(current, 1)
    return days
