import frappe
from frappe import _
import json
from frappe.utils import getdate


def execute(filters=None):
    filters = filters or {}
    project = filters.get("project")
    sprint = filters.get("sprint")
    include_done = filters.get("include_done")

    if not sprint:
        sprint = frappe.db.get_value(
            "Pulse Sprint", {"project": project, "status": "Active"}, "name"
        )

    conditions = []
    if project:
        conditions.append("`tabPulse Task`.`project` = %(project)s")
    if sprint:
        conditions.append("`tabPulse Task`.`pulse_sprint` = %(sprint)s")
    if not include_done:
        conditions.append("`tabPulse Task`.`status` NOT IN ('Completed', 'Cancelled')")

    tasks = frappe.db.sql(
        f"""
        SELECT `tabPulse Task`.`name`, `tabPulse Task`.`_assign`, `tabPulse Task`.`pulse_story_points`,
               `tabPulse Task`.`pulse_sprint`, `tabPulse Task`.`subject`, `tabPulse Task`.`status`
        FROM `tabPulse Task`
        WHERE {" AND ".join(conditions)}
        """,
        {"project": project, "sprint": sprint},
        as_dict=True,
    )

    task_names = [t.name for t in tasks if t._assign]
    if task_names:
        timesheet_hours = dict(
            frappe.db.sql(
                """
                SELECT tsd.task, SUM(tsd.hours)
                FROM `tabTimesheet Detail` tsd
                WHERE tsd.task IN (%s)
                  AND tsd.docstatus = 1
                GROUP BY tsd.task
            """
                % ",".join(frappe.db.escape(n) for n in task_names)
            )
        )
    else:
        timesheet_hours = {}

    assignee_map = {}
    for t in tasks:
        assignees = json.loads(t._assign or "[]")
        pts = float(t.pulse_story_points or 0)
        task_hours = timesheet_hours.get(t.name, 0)
        for user in assignees:
            if user not in assignee_map:
                assignee_map[user] = {
                    "open_tasks": 0,
                    "open_points": 0,
                    "logged_hours": 0,
                }
            assignee_map[user]["open_tasks"] += 1
            assignee_map[user]["open_points"] += pts
            assignee_map[user]["logged_hours"] += task_hours / len(assignees)

    columns = [
        {
            "label": _("Assignee"),
            "fieldname": "assignee",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Open Tasks"),
            "fieldname": "open_tasks",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": _("Open Story Points"),
            "fieldname": "open_points",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": _("Logged Hours"),
            "fieldname": "logged_hours",
            "fieldtype": "Float",
            "width": 130,
            "precision": 1,
        },
        {
            "label": _("Avg Points/Task"),
            "fieldname": "avg_points",
            "fieldtype": "Float",
            "width": 140,
        },
    ]

    data = []
    total_tasks = 0
    total_points = 0
    total_hours = 0
    for user, info in sorted(assignee_map.items()):
        avg = (
            round(info["open_points"] / info["open_tasks"], 1)
            if info["open_tasks"]
            else 0
        )
        data.append(
            {
                "assignee": user,
                "open_tasks": info["open_tasks"],
                "open_points": round(info["open_points"], 1),
                "logged_hours": round(info["logged_hours"], 1),
                "avg_points": avg,
            }
        )
        total_tasks += info["open_tasks"]
        total_points += info["open_points"]
        total_hours += info["logged_hours"]

    data.append(
        {
            "assignee": "<b>" + _("Total") + "</b>",
            "open_tasks": total_tasks,
            "open_points": round(total_points, 1),
            "logged_hours": round(total_hours, 1),
            "avg_points": round(total_points / total_tasks, 1) if total_tasks else 0,
        }
    )

    return columns, data
