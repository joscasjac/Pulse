import frappe


def refresh_project_stats():
    frappe.cache().delete_keys("pulse:project_stats:*")
