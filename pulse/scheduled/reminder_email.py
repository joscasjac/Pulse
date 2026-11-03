"""Transactional email delivery for stable Pulse reminder inbox identities.

Frappe Alert logs intentionally do not send email. Queue these reminder emails
explicitly, using the user's event-reminder feature preference instead of the
notification-type allow-list. Queued means an Email Queue row, not inbox receipt.
"""
from html import escape

import frappe
from frappe.utils import getdate, get_url
from pulse.services.atomic import atomic_scope


def can_read_title_due(user):
    """Task row access alone must not disclose masked or restricted fields."""
    from frappe.model import get_permitted_fields
    allowed = set(get_permitted_fields('Task', user=user, permission_type='read'))
    meta = frappe.get_meta('Task')
    for fieldname in ('subject', 'exp_end_date'):
        field = meta.get_field(fieldname)
        if fieldname not in allowed or not field or field.get('mask'):
            return False
    return True


def email_allowed(user):
    if not frappe.get_cached_doc('Pulse Settings').get('email_notifications'):
        return False
    from frappe.desk.doctype.notification_settings import notification_settings as preferences
    # Both current and earlier Frappe16 treat absent preference rows as enabled.
    enabled = frappe.db.get_value('Notification Settings', user, 'enabled', ignore=True)
    if enabled is not None and not enabled:
        return False
    feature = getattr(preferences, 'is_email_enabled_for_feature', None)
    if callable(feature):
        return bool(feature(user, 'enable_email_event_reminders'))
    for fieldname in ('enable_email_notifications', 'enable_email_event_reminders'):
        value = frappe.db.get_value('Notification Settings', user, fieldname, ignore=True)
        if value is not None and not value:
            return False
    return True


def queue_reminder_email(notification_name, expected_due):
    """Queue at most once per stable reminder, safely retrying failed attempts.

    Re-read lifecycle, due date, assignments and access under current row locks.
    The queue row and queued marker commit together. Failed attempts preserve the
    inbox notification/read state and remain eligible for the scheduler's retry.
    """
    try:
        identity = frappe.db.get_value('Pulse Notification', notification_name,
            ['recipient', 'reference_doctype', 'reference_name'], as_dict=True)
        if not identity or identity.reference_doctype != 'Task' or identity.recipient == 'Guest':
            return False
        with atomic_scope('pulse_reminder_email'):
            # User first matches assignment/offboarding's User-before-Task lock.
            user = frappe.get_doc('User', identity.recipient, for_update=True)
            task = frappe.get_doc('Task', identity.reference_name, for_update=True)
            notification = frappe.get_doc('Pulse Notification', notification_name, for_update=True)
            if notification.get('email_queued'):
                return False
            if notification.recipient != user.name or notification.reference_doctype != 'Task' or notification.reference_name != task.name:
                return False
            if not user.enabled or not user.email or task.get('pulse_archived') or task.status in {'Completed', 'Cancelled'}:
                return False
            if not task.exp_end_date or getdate(task.exp_end_date) != getdate(expected_due):
                return False
            try:
                assignees = frappe.parse_json(task.get('_assign') or '[]')
            except (ValueError, TypeError):
                return False
            if not isinstance(assignees, list) or user.name not in assignees:
                return False
            if not frappe.has_permission('Task', 'read', doc=task, user=user.name) or not can_read_title_due(user.name) or not email_allowed(user.name):
                return False
            message = escape(notification.message or '').replace('\n', '<br>')
            link = get_url(notification.link_url)
            message += '<p><a href="' + escape(link, quote=True) + '">Open task in Pulse</a></p>'
            queue = frappe.sendmail(recipients=[user.email], subject='[Pulse] ' + notification.message,
                message=message, now=False, delayed=True,
                reference_doctype='Pulse Notification', reference_name=notification.name,
                add_unsubscribe_link=0)
            if not getattr(queue, 'name', None) or not frappe.db.exists('Email Queue', queue.name):
                frappe.throw('The reminder email was not added to Email Queue.')
            frappe.db.set_value('Pulse Notification', notification.name, 'email_queued', 1, update_modified=False)
            return True
    except Exception:
        frappe.log_error(title='Pulse reminder email queue failed',
            message='Reminder ' + str(notification_name) + ' was not marked queued; the scheduler may retry.\n' + frappe.get_traceback())
        return False
