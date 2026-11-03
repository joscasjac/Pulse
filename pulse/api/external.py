"""Explicitly shared task portal. No project membership or internal feed exposure."""
import hashlib
import frappe
from pulse.hooks.permissions import require_permission


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 140:
        frappe.throw(f'Provide an exact {label} record ID.')
    return value


def _signed_in(lock=False):
    user = frappe.session.user
    if user == 'Guest' or not frappe.db.get_value('User', user, 'enabled', for_update=lock):
        frappe.throw('Sign in to view shared work.', frappe.PermissionError)
    return user


def _manager(task, lock=False):
    _identifier(task, 'task')
    _signed_in(lock=lock)
    doc = require_permission('Task', task, 'write')
    doc.check_permission('read')
    doc.check_permission('share')
    if lock:
        frappe.db.sql('SELECT name FROM `tabTask` WHERE name=%s FOR UPDATE', (task,))
        doc.reload()
        _signed_in()
        doc.check_permission('write')
        doc.check_permission('share')
    return doc


def _shared(task, lock=False):
    _identifier(task, 'task')
    user = _signed_in(lock=lock)
    if lock:
        frappe.db.sql('SELECT name FROM `tabTask` WHERE name=%s FOR UPDATE', (task,))
        _signed_in()
    if not frappe.db.get_value('Pulse External Share', {'user': user, 'task': task, 'enabled': 1}, 'name', for_update=lock):
        frappe.throw('This task is not shared with you.', frappe.PermissionError)
    return frappe.get_doc('Task', task)


def _dto(doc):
    # Description, attachments, assignees, customer/commercial links and internal
    # comments deliberately stay out of this external boundary.
    return {'name': doc.name, 'issue_key': doc.get('issue_key'), 'subject': doc.subject,
            'status': doc.get('workflow_state') or doc.status, 'start_date': doc.exp_start_date,
            'due_date': doc.exp_end_date, 'modified': str(doc.modified)}


@frappe.whitelist()
def shared_tasks():
    user = _signed_in()
    names = frappe.get_all('Pulse External Share', filters={'user': user, 'enabled': 1}, pluck='task', limit_page_length=0)
    return [_dto(_shared(name)) for name in names if frappe.db.exists('Task', name)]


@frappe.whitelist()
def task(task):
    doc = _shared(task)
    comments = frappe.get_all('Pulse External Comment', filters={'task': task}, fields=['name', 'content', 'creation'], order_by='creation asc', limit_page_length=100)
    return {'task': _dto(doc), 'comments': comments}


@frappe.whitelist(methods=['POST'])
def comment(task, content):
    _shared(task, lock=True)
    if not isinstance(content, str) or not content.strip() or len(content) > 5000:
        frappe.throw('Enter a comment of up to 5,000 characters.')
    return frappe.get_doc({'doctype': 'Pulse External Comment', 'task': task,
        'content': content.strip()}).insert(ignore_permissions=True).name


@frappe.whitelist()
def sharing(task):
    _manager(task)
    return {'shares': frappe.get_all('Pulse External Share', filters={'task': task, 'enabled': 1}, fields=['user'], limit_page_length=0),
            'candidates': frappe.get_all('User', filters={'enabled': 1, 'user_type': 'Website User', 'name': ['not in', ['Guest', 'Administrator']]}, fields=['name', 'full_name'], limit_page_length=0)}


@frappe.whitelist(methods=['POST'])
def share(task, user):
    _identifier(user, 'user')
    _manager(task)
    # Current User locks serialize new grants with organization offboarding.
    for account in sorted({frappe.session.user, user}):
        frappe.db.get_value('User', account, 'enabled', for_update=True)
    doc = _manager(task, lock=True)
    for fieldname in ('issue_key', 'subject', 'status', 'workflow_state', 'exp_start_date', 'exp_end_date'):
        field = doc.meta.get_field(fieldname)
        if field and (field.get('mask') or not doc.has_permlevel_access_to(fieldname, df=field, permission_type='read')):
            frappe.throw('You cannot share task fields that you are not permitted to read.', frappe.PermissionError)
    target = frappe.db.get_value('User', user, ['enabled', 'user_type'], as_dict=True, for_update=True)
    if user in ('Guest', 'Administrator') or not target or not target.enabled or target.user_type != 'Website User':
        frappe.throw('Choose an enabled external website user.')
    # Native Task DocShare would also expose the full Task through core APIs.
    # This portal grant intentionally confers no native Task/project permission.
    key = 'external-' + hashlib.sha256((task + ':' + user).encode()).hexdigest()
    if frappe.db.exists('Pulse External Share', key):
        frappe.db.set_value('Pulse External Share', key, 'enabled', 1)
    else:
        frappe.get_doc({'doctype': 'Pulse External Share', 'task': task, 'user': user,
            'enabled': 1}).insert(ignore_permissions=True, set_name=key)
    return {'task': task, 'user': user, 'url': '/pulse/external'}


@frappe.whitelist(methods=['POST'])
def revoke(task, user):
    _identifier(user, 'user')
    _manager(task, lock=True)
    for name in frappe.get_all('Pulse External Share', filters={'task': task, 'user': user}, pluck='name'):
        frappe.db.set_value('Pulse External Share', name, 'enabled', 0)
    return {'revoked': user}


@frappe.whitelist()
def discussion(task):
    _manager(task)
    return frappe.get_all('Pulse External Comment', filters={'task': task}, fields=['name', 'content', 'creation'], order_by='creation asc', limit_page_length=100)


@frappe.whitelist(methods=['POST'])
def reply(task, content):
    _manager(task, lock=True)
    if not isinstance(content, str) or not content.strip() or len(content) > 5000:
        frappe.throw('Enter a comment of up to 5,000 characters.')
    return frappe.get_doc({'doctype': 'Pulse External Comment', 'task': task,
        'content': content.strip()}).insert(ignore_permissions=True).name
