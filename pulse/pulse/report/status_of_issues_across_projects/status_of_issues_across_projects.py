import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Pulse Project", "width": 200},
        {"label": _("To Do"), "fieldname": "to_do", "fieldtype": "Int", "width": 100},
        {"label": _("In Progress"), "fieldname": "in_progress", "fieldtype": "Int", "width": 100},
        {"label": _("In Review"), "fieldname": "in_review", "fieldtype": "Int", "width": 100},
        {"label": _("Done"), "fieldname": "done", "fieldtype": "Int", "width": 100},
        {"label": _("Cancelled"), "fieldname": "cancelled", "fieldtype": "Int", "width": 100},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "width": 100},
    ]

    # Fetch all tasks
    tasks = frappe.get_all("Pulse Task", fields=["name", "project", "status"])

    # Mapping status to columns
    status_map = {
        "Open": "to_do",
        "To Do": "to_do",
        "Working": "in_progress",
        "In Progress": "in_progress",
        "Pending Review": "in_review",
        "In Review": "in_review",
        "Completed": "done",
        "Done": "done",
        "Cancelled": "cancelled"
    }

    project_data = {}
    for t in tasks:
        proj = t.project or "Unassigned Project"
        state = t.status
        col = status_map.get(state, "to_do")
        
        if proj not in project_data:
            project_data[proj] = {
                "project": proj,
                "to_do": 0,
                "in_progress": 0,
                "in_review": 0,
                "done": 0,
                "cancelled": 0,
                "total": 0
            }
        project_data[proj][col] += 1
        project_data[proj]["total"] += 1

    data = sorted(project_data.values(), key=lambda x: x["project"])
    return columns, data
