import frappe
from frappe.model.document import Document


class PulseComment(Document):
    def after_insert(self):
        self.create_activity_log()
        self.send_mention_notifications()

    def create_activity_log(self):
        try:
            frappe.get_doc({
                'doctype': 'Pulse Activity Log',
                'user': frappe.session.user,
                'activity_type': 'Comment Added',
                'reference_doctype': 'Task',
                'reference_name': self.task,
                'description': 'commented on task',
                'project': self.project,
            }).insert(ignore_permissions=True)
        except Exception:
            pass

    def send_mention_notifications(self):
        if frappe.flags.get("pulse_migration"):
            return
        import json
        try:
            mentioned = json.loads(self.mentioned_users or '[]')
        except Exception:
            mentioned = []
        for user in mentioned:
            if user and user != frappe.session.user and frappe.has_permission("Task", "read", doc=self.task, user=user):
                try:
                    frappe.get_doc({
                        'doctype': 'Pulse Notification',
                        'recipient': user,
                        'notification_type': 'Mention',
                        'reference_doctype': 'Task',
                        'reference_name': self.task,
                        'message': f'{frappe.session.user} mentioned you in a comment on task {self.task}',
                        'is_read': 0,
                    }).insert(ignore_permissions=True)
                    frappe.publish_realtime('pulse_notification', {
                        'recipient': user,
                        'type': 'mention',
                        'task': self.task,
                        'message': f'{frappe.session.user} mentioned you',
                    }, user=user)
                except Exception:
                    pass
