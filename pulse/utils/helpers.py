import frappe


def get_project_key(project_name):
    return frappe.db.get_value("Pulse Project", project_name, "pulse_project_key")


def get_cached_project_stats(project_name):
    cache_key = f"pulse:project_stats:{project_name}"
    stats = frappe.cache().get_value(cache_key)
    if stats:
        return stats
    total = frappe.db.count("Pulse Task", {"project": project_name})
    completed = frappe.db.count(
        "Pulse Task", {"project": project_name, "status": "Completed"}
    )
    stats = {
        "total_tasks": total,
        "completed_tasks": completed,
        "percent_complete": round((completed / total * 100), 1) if total > 0 else 0,
    }
    frappe.cache().set_value(cache_key, stats, expires_in_sec=300)
    return stats
