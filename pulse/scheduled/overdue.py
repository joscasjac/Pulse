"""Notify permitted assignees about overdue native Tasks without changing status."""

import frappe
from frappe.utils import today


def flag_overdue_tasks():
    # Scheduler enumeration is elevated, but each recipient is checked against
    # current Task permissions before any subject or reference is disclosed.
    tasks = frappe.get_all(
        "Task",
        filters={
            "exp_end_date": ["<", today()],
            "status": ["not in", ("Completed", "Cancelled")],
            "pulse_archived": 0,
        },
        fields=["name", "subject", "_assign"],
    )
    for task in tasks:
        try:
            assignees = frappe.parse_json(task._assign or "[]")
        except (TypeError, ValueError):
            assignees = []
        if not isinstance(assignees, list):
            continue
        for user in {value for value in assignees if isinstance(value, str)}:
            if user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
                continue
            if not frappe.has_permission("Task", "read", doc=task.name, user=user):
                continue
            # Insert documents, rather than bulk SQL, so Notification Log's
            # validation, realtime delivery and notification settings run.
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": user,
                "type": "Alert",
                "document_type": "Task",
                "document_name": task.name,
                "subject": frappe._("Overdue: {0}").format(task.subject),
            }).insert(ignore_permissions=True)
