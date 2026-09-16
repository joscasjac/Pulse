"""Advance reminders through Frappe's notification preferences and email queue."""
import hashlib
from urllib.parse import quote

import frappe
from frappe.utils import add_days, today, get_url


def parse_reminder_days(value):
    try:
        days = {int(part.strip()) for part in (value or "3, 1, 0").split(",")}
    except (ValueError, AttributeError):
        raise ValueError("Reminder days must be comma-separated whole numbers.")
    if any(day < 0 or day > 365 for day in days):
        raise ValueError("Reminder days must be between 0 and 365.")
    return sorted(days)


def send_advance_reminders():
    settings = frappe.get_cached_doc("Pulse Settings")
    if not settings.get("advance_reminders"):
        return
    for days in parse_reminder_days(settings.get("reminder_days_before")):
        due = add_days(today(), days)
        tasks = frappe.get_all("Task", filters=[
            ["exp_end_date", ">=", due], ["exp_end_date", "<", add_days(due, 1)],
            ["status", "not in", ["Completed", "Cancelled"]], ["pulse_archived", "=", 0]],
            fields=["name", "subject", "_assign"])
        for task in tasks:
            try:
                users = frappe.parse_json(task._assign or "[]")
            except (ValueError, TypeError):
                continue
            if not isinstance(users, list):
                continue
            for user in {u for u in users if isinstance(u, str)}:
                if user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
                    continue
                if not frappe.has_permission("Task", "read", doc=task.name, user=user):
                    continue
                # Stable per recipient, due date and threshold: retries cannot
                # enqueue another reminder; rescheduling creates a new reminder.
                key = hashlib.sha256(f"{task.name}|{user}|{due}|{days}".encode()).hexdigest()
                name = "pulse-reminder-" + key
                label = frappe._("Due today") if days == 0 else frappe._("Due in {0} days").format(days)
                if days == 1:
                    label = frappe._("Due tomorrow")
                message = f"{label}: {task.subject}"
                if not frappe.db.exists("Pulse Notification", name):
                    try:
                        frappe.get_doc({"doctype": "Pulse Notification", "recipient": user,
                            "notification_type": "Due Reminder", "reference_doctype": "Task",
                            "reference_name": task.name, "message": message,
                            "link_url": "/pulse/board?task=" + quote(task.name, safe="")
                        }).insert(ignore_permissions=True, set_name=name)
                        frappe.publish_realtime("pulse_notification", {"refresh": True}, user=user, after_commit=True)
                    except frappe.DuplicateEntryError:
                        pass
                if frappe.db.exists("Notification Log", name):
                    continue
                doc = frappe.get_doc({"doctype": "Notification Log", "for_user": user,
                    "type": "Alert", "document_type": "Task", "document_name": task.name,
                    "subject": message,
                    "link": get_url("/pulse/board?task=" + quote(task.name, safe=""))})
                try:
                    doc.insert(ignore_permissions=True, set_name=name)
                except frappe.DuplicateEntryError:
                    pass
