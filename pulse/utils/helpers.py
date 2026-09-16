"""Permission-aware helpers for native ERPNext projects."""
import frappe
from pulse.hooks.permissions import require_permission


def get_project_key(project_name):
    return require_permission("Project", project_name).get("pulse_project_key")


def get_cached_project_stats(project_name):
    # Keep the public helper name, but do not cache user-dependent counts across
    # permission or membership changes. Project access does not imply all tasks.
    require_permission("Project", project_name)
    tasks = frappe.get_list("Task", filters={"project": project_name, "pulse_archived": 0},
                            fields=["status"], limit_page_length=0)
    total = len(tasks)
    completed = sum(task.status == "Completed" for task in tasks)
    return {"total_tasks": total, "completed_tasks": completed,
            "percent_complete": round(completed / total * 100, 1) if total else 0}
