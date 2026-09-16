import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
        {"label": _("Backlog"), "fieldname": "backlog", "fieldtype": "Int", "width": 100},
        {"label": _("Blocked"), "fieldname": "blocked", "fieldtype": "Int", "width": 100},
        {"label": _("To Do"), "fieldname": "to_do", "fieldtype": "Int", "width": 100},
        {"label": _("In Progress"), "fieldname": "in_progress", "fieldtype": "Int", "width": 100},
        {"label": _("In Review"), "fieldname": "in_review", "fieldtype": "Int", "width": 100},
        {"label": _("Done"), "fieldname": "done", "fieldtype": "Int", "width": 100},
        {"label": _("Cancelled"), "fieldname": "cancelled", "fieldtype": "Int", "width": 100},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 100},
    ]

    from pulse.api.task_config import statuses_for
    from pulse.hooks.permissions import require_permission
    projects = frappe.get_list("Project", pluck="name", limit_page_length=0)
    if not projects:
        return columns, []
    categories = {project: {row["label"]: row["category"]
                           for row in statuses_for(require_permission("Project", project))}
                  for project in projects}
    tasks = frappe.get_list("Task", filters={"project": ["in", projects], "pulse_archived": 0},
                            fields=["project", "status", "workflow_state"], limit_page_length=0)
    status_map = {"Open": "to_do", "Backlog": "backlog", "To Do": "to_do",
                  "Working": "in_progress", "In Progress": "in_progress",
                  "Pending Review": "in_review", "In Review": "in_review",
                  "Blocked": "blocked", "Completed": "done", "Done": "done",
                  "Cancelled": "cancelled"}
    project_data = {}
    for task in tasks:
        state = categories[task.project].get(task.workflow_state, task.status)
        row = project_data.setdefault(task.project, {"project": task.project,
              **{key: 0 for key in set(status_map.values())}, "total": 0})
        row[status_map.get(state, "to_do")] += 1
        row["total"] += 1
    return columns, sorted(project_data.values(), key=lambda row: row["project"])
