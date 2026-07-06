import frappe
from frappe import _
from frappe.utils import getdate, add_days


STATES = ["Backlog", "To Do", "In Progress", "In Review", "Done"]


def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")
    sprint = filters.get("sprint")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not project:
        return [], []

    conditions = ["`tabPulse Task Status Log`.`project` = %(project)s"]
    if sprint:
        conditions.append("`tabPulse Task Status Log`.`sprint` = %(sprint)s")

    log_rows = frappe.db.sql(
        f"""
        SELECT `tabPulse Task Status Log`.`task`, `tabPulse Task Status Log`.`to_state`,
               `tabPulse Task Status Log`.`changed_on`, `tabPulse Task Status Log`.`project`
        FROM `tabPulse Task Status Log`
        WHERE {" AND ".join(conditions)}
        ORDER BY `tabPulse Task Status Log`.`changed_on` ASC
        """,
        {"project": project, "sprint": sprint},
        as_dict=True,
    )

    if not log_rows:
        return [], []

    dates = set()
    for r in log_rows:
        dates.add(getdate(r.changed_on))
    if from_date:
        dates.add(getdate(from_date))
    if to_date:
        dates.add(getdate(to_date))
    sorted_dates = sorted(dates)

    columns = [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
    ]
    for s in STATES:
        columns.append(
            {
                "label": _(s),
                "fieldname": s.lower().replace(" ", "_"),
                "fieldtype": "Int",
                "width": 100,
            }
        )

    data = []
    for day in sorted_dates:
        day_end = day.strftime("%Y-%m-%d 23:59:59")
        day_after = day.strftime("%Y-%m-%d 00:00:00")

        task_latest_state = {}
        for r in log_rows:
            rd = getdate(r.changed_on)
            if rd <= day:
                task = r.task
                if task not in task_latest_state or getdate(r.changed_on) >= getdate(
                    task_latest_state[task][1]
                ):
                    task_latest_state[task] = (r.to_state, r.changed_on)

        counts = {s: 0 for s in STATES}
        for task, (state, changed_on) in task_latest_state.items():
            if state in counts:
                counts[state] += 1

        row = {"date": day}
        for s in STATES:
            row[s.lower().replace(" ", "_")] = counts[s]
        data.append(row)

    return columns, data
