import frappe
from frappe import _
from frappe.utils import getdate, add_days


def execute(filters=None):
    filters = filters or {}
    sprint_name = filters.get("sprint")
    if not sprint_name:
        project = filters.get("project")
        if project:
            sprint_name = frappe.db.get_value(
                "Pulse Sprint", {"project": project, "status": "Active"}, "name"
            )
    if not sprint_name:
        return [], []

    sprint = frappe.get_doc("Pulse Sprint", sprint_name)
    if not sprint.start_date or not sprint.end_date:
        return [], []

    from_date = getdate(sprint.start_date)
    to_date = getdate(sprint.end_date)
    planned = flt(sprint.planned_points)

    log_rows = frappe.get_all(
        "Pulse Task Status Log",
        filters={"sprint": sprint_name},
        fields=["task", "to_state", "changed_on", "points_at_change"],
        order_by="changed_on asc",
    )

    completed_by_day = {}
    added_by_day = {}
    for r in log_rows:
        day = getdate(r.changed_on)
        if r.to_state == "Done":
            completed_by_day[day] = completed_by_day.get(day, 0) + flt(
                r.points_at_change
            )
        else:
            added_by_day[day] = added_by_day.get(day, 0) + flt(r.points_at_change)

    holiday_list = get_holiday_list(getattr(sprint, "project", None))
    total_working_days = count_working_days(from_date, to_date, holiday_list)
    working_days_before = {}

    cumulative_working = 0
    current = from_date
    while current <= to_date:
        is_working = current.weekday() < 5 and (
            not holiday_list or getdate(current) not in get_holidays(holiday_list)
        )
        if is_working:
            cumulative_working += 1
        working_days_before[current] = cumulative_working
        current = add_days(current, 1)

    columns = [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
        {
            "label": _("Ideal Remaining"),
            "fieldname": "ideal_remaining",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": _("Actual Remaining"),
            "fieldname": "actual_remaining",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": _("Completed That Day"),
            "fieldname": "completed_day",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": _("Added That Day"),
            "fieldname": "added_day",
            "fieldtype": "Float",
            "width": 140,
        },
    ]

    ideal_per_working_day = planned / total_working_days if total_working_days else 0
    num_days = (to_date - from_date).days or 1

    data = []
    cumulative_completed = 0
    cumulative_added = 0
    for i in range(num_days + 1):
        day = add_days(from_date, i)
        if day > to_date:
            day = to_date
        day_completed = completed_by_day.get(day, 0)
        day_added = added_by_day.get(day, 0)
        cumulative_completed += day_completed
        cumulative_added += day_added

        actual_remaining = (planned + cumulative_added) - cumulative_completed

        wd_so_far = working_days_before.get(day, 0)
        ideal_remaining = planned - (ideal_per_working_day * wd_so_far)
        if ideal_remaining < 0:
            ideal_remaining = 0

        data.append(
            {
                "date": day,
                "ideal_remaining": round(ideal_remaining, 1),
                "actual_remaining": round(actual_remaining, 1),
                "completed_day": round(day_completed, 1),
                "added_day": round(day_added, 1),
            }
        )
        if day >= to_date:
            break

    return columns, data


def get_holiday_list(project):
    if not project:
        return None
    holiday_list = frappe.db.get_value("Pulse Project", project, "holiday_list")
    if not holiday_list:
        holiday_list = frappe.db.get_single_value(
            "Pulse Settings", "working_days_source"
        )
    return holiday_list


_holidays_cache = {}


def get_holidays(holiday_list):
    if holiday_list not in _holidays_cache:
        _holidays_cache[holiday_list] = {
            getdate(h)
            for h in frappe.get_all(
                "Holiday", filters={"parent": holiday_list}, pluck="holiday_date"
            )
        }
    return _holidays_cache[holiday_list]


def count_working_days(start_date, end_date, holiday_list=None):
    if start_date > end_date:
        return 0
    holidays = get_holidays(holiday_list) if holiday_list else set()
    days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current = add_days(current, 1)
    return days


def flt(v):
    return float(v or 0)
