"""One transactional overdue email per recipient and site-local day."""
import hashlib
from html import escape
from urllib.parse import quote

import frappe
from frappe.utils import getdate, get_url
from pulse.scheduled.reminder_email import can_read_title_due, email_allowed
from pulse.services.atomic import atomic_scope


def digest_name(user, reminder_date):
    key = hashlib.sha256(f'{user}|{reminder_date}'.encode()).hexdigest()
    return 'pulse-overdue-digest-' + key


def queue_overdue_digest(user_name, task_names, reminder_date):
    """Recheck candidates under locks; queue and daily marker succeed together.

    The User lock serializes a recipient's attempts. The unique notification name
    is a second guard against overlapping transactions with stale read snapshots.
    Native Email Queue owns transport retries once the transaction commits.
    """
    name = digest_name(user_name, reminder_date)
    try:
        with atomic_scope('pulse_overdue_digest'):
            user = frappe.get_doc('User', user_name, for_update=True)
            if user.name == 'Guest' or not user.enabled or not user.email:
                return False
            if frappe.db.get_value('Pulse Notification', name, 'name', for_update=True):
                return False
            if not can_read_title_due(user.name) or not email_allowed(user.name):
                return False
            items = []
            for task_name in sorted(set(task_names)):
                try:
                    task = frappe.get_doc('Task', task_name, for_update=True)
                except frappe.DoesNotExistError:
                    continue
                if task.get('pulse_archived') or task.status in {'Completed', 'Cancelled'}:
                    continue
                if not task.exp_end_date or getdate(task.exp_end_date) >= getdate(reminder_date):
                    continue
                try:
                    assignees = frappe.parse_json(task.get('_assign') or '[]')
                except (TypeError, ValueError):
                    continue
                if not isinstance(assignees, list) or user.name not in assignees:
                    continue
                if not frappe.has_permission('Task', 'read', doc=task, user=user.name):
                    continue
                link = get_url('/pulse/board?task=' + quote(task.name, safe=''))
                items.append((getdate(task.exp_end_date), task.name,
                    '<li><a href="' + escape(link, quote=True) + '">' +
                    escape(task.subject or task.name) + '</a> — ' +
                    escape(str(getdate(task.exp_end_date))) + '</li>'))
            if not items:
                return False
            subject = frappe._('Overdue tasks: {0}').format(len(items))
            message = '<p>' + escape(frappe._('Your overdue tasks as of {0}').format(reminder_date)) + '</p><ul>'
            message += ''.join(item[2] for item in sorted(items)) + '</ul>'
            # Insert before sendmail: a duplicate key cannot create a second queue.
            notification = frappe.get_doc({
                'doctype': 'Pulse Notification', 'recipient': user.name,
                'notification_type': 'Due Reminder', 'message': subject,
                'link_url': '/pulse',
            }).insert(ignore_permissions=True, set_name=name)
            # Frappe hash-autoname DocTypes may silently rename on a PK collision.
            # Reject that fallback inside the savepoint before any email is queued.
            if notification.name != name:
                raise frappe.DuplicateEntryError('Overdue digest identity already exists')
            queue = frappe.sendmail(recipients=[user.email], subject='[Pulse] ' + subject,
                message=message, now=False, delayed=True,
                reference_doctype='Pulse Notification', reference_name=name,
                add_unsubscribe_link=0)
            if not getattr(queue, 'name', None) or not frappe.db.exists('Email Queue', queue.name):
                frappe.throw('The overdue summary was not added to Email Queue.')
            frappe.db.set_value('Pulse Notification', name, 'email_queued', 1, update_modified=False)
            frappe.publish_realtime('pulse_notification', {'refresh': True}, user=user.name, after_commit=True)
            return True
    except frappe.DuplicateEntryError:
        # A competing run committed the same day's identity; our savepoint rolled back.
        return False
    except Exception:
        frappe.log_error(title='Pulse overdue digest queue failed',
            message='Digest ' + name + ' was not queued; the scheduler may retry.\n' + frappe.get_traceback())
        return False
