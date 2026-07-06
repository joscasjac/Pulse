"""Overdue handling — NON-destructive.

The previous version force-set overdue tasks to 'In Progress' every night,
silently overwriting user actions. That is removed. Overdue is a DERIVED
condition (exp_end_date < today and not done); we never mutate status.

This job notifies each assignee of their overdue, open tasks once per run,
reusing Frappe's Notification Log. It writes no status.
"""

import frappe
from frappe.utils import today


OPEN_STATES = ("Backlog", "To Do", "In Progress", "In Review")


def flag_overdue_tasks():
    tasks = frappe.get_all(
        "Pulse Task",
        filters={
            "exp_end_date": ["<", today()],
            "status": ["not in", ("Completed", "Cancelled")],
        },
        fields=["name", "subject", "_assign"],
    )
    logs = []
    for t in tasks:
        assignees = frappe.parse_json(t._assign or "[]")
        for user in assignees:
            logs.append(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Pulse Task",
                    "document_name": t.name,
                    "subject": frappe._("Overdue: {0}").format(t.subject),
                }
            )
    if logs:
        try:
            frappe.db.bulk_insert("Notification Log", logs, ignore_permissions=True)
        except Exception:
            frappe.log_error(
                title="Pulse: overdue notification batch failed",
                message=frappe.get_traceback(),
            )
