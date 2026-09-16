import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"label": _("Sprint"), "fieldname": "sprint", "fieldtype": "Data", "width": 200},
        {"label": _("Issues"), "fieldname": "issues", "fieldtype": "Int", "width": 100},
        {"label": _("Percentage"), "fieldname": "percentage", "fieldtype": "Percent", "width": 100},
    ]

    active_sprints = frappe.get_list("Pulse Sprint", filters={"status": "Active"},
                                     fields=["name", "sprint_name"], limit_page_length=0)
    if not active_sprints:
        return columns, []
    tasks = frappe.get_list("Task", filters={"pulse_archived": 0,
                            "pulse_sprint": ["in", [s.name for s in active_sprints]]},
                            fields=["pulse_sprint"], limit_page_length=0)
    counts = {}
    for task in tasks:
        counts[task.pulse_sprint] = counts.get(task.pulse_sprint, 0) + 1
    total = len(tasks)
    data = [{"sprint": sprint.sprint_name or sprint.name,
             "issues": counts.get(sprint.name, 0),
             "percentage": counts.get(sprint.name, 0) / total * 100 if total else 0}
            for sprint in active_sprints]
    return columns, data
