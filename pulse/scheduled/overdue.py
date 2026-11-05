"""Notify permitted assignees about overdue native Tasks without changing status."""

import hashlib
from urllib.parse import quote

import frappe
from frappe.utils import today, get_url
from pulse.scheduled.reminder_email import can_read_title_due
from pulse.scheduled.overdue_digest import queue_overdue_digest


def flag_overdue_tasks():
    # Scheduler enumeration is elevated, but each recipient is checked against
    # current Task permissions before any subject or reference is disclosed.
    reminder_date = today()
    tasks = frappe.get_all(
        "Task",
        filters={
            "exp_end_date": ["<", reminder_date],
            "status": ["not in", ("Completed", "Cancelled")],
            "pulse_archived": 0,
        },
        fields=["name", "subject", "_assign", "exp_end_date"],
    )
    recipients = {}
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
            if not frappe.has_permission("Task", "read", doc=task.name, user=user) or not can_read_title_due(user):
                continue
            # Once per site-local day and due date; retries must not requeue
            # email or reset a read inbox item. A reschedule starts a new identity.
            key = hashlib.sha256(f"{task.name}|{user}|{task.exp_end_date}|{reminder_date}".encode()).hexdigest()
            name = "pulse-overdue-" + key
            subject = frappe._("Overdue: {0}").format(task.subject)
            link = "/pulse/board?task=" + quote(task.name, safe="")
            if not frappe.db.exists("Pulse Notification", name):
                try:
                    frappe.get_doc({
                        "doctype": "Pulse Notification", "recipient": user,
                        "notification_type": "Due Reminder", "reference_doctype": "Task",
                        "reference_name": task.name, "message": subject, "link_url": link,
                    }).insert(ignore_permissions=True, set_name=name)
                    frappe.publish_realtime("pulse_notification", {"refresh": True}, user=user, after_commit=True)
                except frappe.DuplicateEntryError:
                    pass
            if not frappe.db.exists("Notification Log", name):
                try:
                    frappe.get_doc({
                        "doctype": "Notification Log", "for_user": user, "type": "Alert",
                        "document_type": "Task", "document_name": task.name,
                        "subject": subject, "link": get_url(link),
                    }).insert(ignore_permissions=True, set_name=name)
                except frappe.DuplicateEntryError:
                    pass
            recipients.setdefault(user, []).append(task.name)
    for user in sorted(recipients):
        queue_overdue_digest(user, recipients[user], reminder_date)
