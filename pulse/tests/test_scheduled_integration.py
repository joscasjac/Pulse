"""Native scheduled reminders exercised through real Notification Log hooks."""
import frappe
from unittest.mock import patch
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


class TestScheduledIntegration(IntegrationTestCase):
    def test_advance_reminders_email_once_and_respect_permissions(self):
        from pulse.scheduled import reminders
        frappe.set_user("Administrator")
        task = frappe.get_doc({"doctype": "Task", "subject": "Advance reminder acceptance",
            "exp_end_date": add_days(today(), 1)}).insert()
        row = frappe._dict(name=task.name, subject=task.subject, _assign='["Administrator"]')
        settings = frappe._dict(advance_reminders=1, reminder_days_before="1")
        get_cached_doc = frappe.get_cached_doc
        get_all = frappe.get_all
        try:
            with patch.object(frappe, "get_cached_doc", side_effect=lambda dt, *a, **kw: settings if dt == "Pulse Settings" else get_cached_doc(dt, *a, **kw)), patch.object(
                frappe, "get_all", side_effect=lambda dt, *a, **kw: [row] if dt == "Task" else get_all(dt, *a, **kw)
            ), patch("frappe.desk.doctype.notification_log.notification_log.is_email_notifications_enabled_for_type", return_value=True), patch.object(
                frappe, "sendmail"
            ) as send:
                reminders.send_advance_reminders()
                reminders.send_advance_reminders()
                self.assertEqual(send.call_count, 1)
                self.assertIn("Due tomorrow", send.call_args.kwargs["subject"])
                self.assertEqual(frappe.db.count("Notification Log", {"document_name": task.name}), 1)
                self.assertEqual(frappe.db.count("Pulse Notification", {"reference_name": task.name}), 1)
                from pulse.api.personal import inbox, mark_read
                notice = next(row for row in inbox() if row.reference_name == task.name)
                self.assertEqual(notice.notification_type, "Due Reminder")
                mark_read(notice.name)
                self.assertFalse(any(row.reference_name == task.name for row in inbox(unread_only=1)))
                frappe.db.delete("Notification Log", {"document_name": task.name})
                frappe.db.delete("Pulse Notification", {"reference_name": task.name})
                with patch.object(frappe, "has_permission", return_value=False):
                    reminders.send_advance_reminders()
                self.assertEqual(send.call_count, 1)
                self.assertEqual(frappe.db.count("Notification Log", {"document_name": task.name}), 0)
        finally:
            frappe.db.delete("Notification Log", {"document_name": task.name})
            frappe.db.delete("Pulse Notification", {"reference_name": task.name})
            from pulse.api.spa import delete_task
            delete_task(task.name)

    def test_overdue_notification_uses_native_task_and_excludes_archive(self):
        from pulse.scheduled.overdue import flag_overdue_tasks
        frappe.set_user("Administrator")
        project = frappe.get_doc({"doctype": "Project", "project_name": "Reminder " + frappe.generate_hash(length=8)}).insert()
        tasks = []
        try:
            for archived in (0, 1):
                task = frappe.get_doc({"doctype": "Task", "subject": "Scheduled reminder test",
                    "project": project.name, "exp_end_date": add_days(today(), -3),
                    "pulse_archived": archived}).insert()
                task.db_set("_assign", '["Administrator"]')
                tasks.append(task)
            before = {task.name: frappe.db.count("Notification Log", {"document_type": "Task", "document_name": task.name}) for task in tasks}
            flag_overdue_tasks()
            self.assertEqual(frappe.db.count("Notification Log", {"document_type": "Task", "document_name": tasks[0].name}), before[tasks[0].name] + 1)
            self.assertEqual(frappe.db.count("Notification Log", {"document_type": "Task", "document_name": tasks[1].name}), before[tasks[1].name])
            for task in tasks:
                self.assertEqual(frappe.db.get_value("Task", task.name, "status"), task.status)
        finally:
            from pulse.api.spa import delete_task
            for task in tasks:
                frappe.db.delete("Notification Log", {"document_type": "Task", "document_name": task.name})
                delete_task(task.name)
            frappe.delete_doc("Project", project.name, force=True)
