"""Task approvals tied to a material content version and an authorized reviewer."""
import hashlib
import json
from contextlib import contextmanager
from urllib.parse import quote
import frappe
from frappe.utils import now_datetime
from pulse.hooks.permissions import require_permission


def content_hash(task):
    fields = {'project', 'subject', 'description', 'priority', 'type', 'exp_start_date',
              'exp_end_date', 'expected_time', 'pulse_story_points', '_assign'}
    if task.project:
        project = frappe.get_doc('Project', task.project)
        fields |= {row.fieldname for row in project.get('pulse_task_field_rules') or []}
    content = {key: task.get(key) for key in sorted(fields)}
    content['labels'] = sorted(row.label for row in task.get('pulse_labels') or [])
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def validate_config(project, statuses):
    if project.get('pulse_approval_statuses') is not None and not isinstance(project.get('pulse_approval_statuses'), str):
        frappe.throw('Approval status names must be text, one status per line.')
    required = [value.strip() for value in (project.get('pulse_approval_statuses') or '').splitlines() if value.strip()]
    if set(required) - set(statuses):
        frappe.throw('Approval requirements must use configured task statuses.')
    from pulse.api.task_config import statuses_for
    initial = {row['label'] for row in statuses_for(project) if row['category'] not in {'Done', 'Cancelled'}}
    if required and not initial - set(required):
        frappe.throw('Keep at least one unfinished status available without prior approval so new tasks can be created.')
    before = project.get_doc_before_save()
    if (before.get('pulse_approval_statuses') if before else '') != project.get('pulse_approval_statuses') and required:
        if frappe.session.user != 'Administrator' and not set(frappe.get_roles()) & {'Pulse Admin', 'System Manager'}:
            frappe.throw('Only an administrator can change approval requirements.', frappe.PermissionError)
    if before and before.get('pulse_approval_statuses') and not required:
        if frappe.session.user != 'Administrator' and not set(frappe.get_roles()) & {'Pulse Admin', 'System Manager'}:
            frappe.throw('Only an administrator can change approval requirements.', frappe.PermissionError)
    project.pulse_approval_statuses = '\n'.join(dict.fromkeys(required))


def validate_task(task, project):
    if not project or task.workflow_state not in (project.get('pulse_approval_statuses') or '').splitlines():
        return
    approved = [] if task.is_new() else frappe.get_all('Pulse Task Approval', filters={'task': task.name,
        'content_hash': content_hash(task), 'decision': 'Approved'}, fields=['reviewer', 'requested_by'], limit_page_length=0)
    valid = any(row.reviewer != row.requested_by and frappe.db.get_value('User', row.reviewer, 'enabled')
                and frappe.has_permission('Task', 'write', doc=task, user=row.reviewer) for row in approved)
    if not valid:
        frappe.throw('This task needs approval for its current content from an enabled reviewer with task access before entering ' + task.workflow_state + '.')


@contextmanager
def _action():
    previous = frappe.flags.get('pulse_approval_action')
    from pulse.services.atomic import atomic_scope
    frappe.flags.pulse_approval_action = True
    try:
        with atomic_scope('pulse_approval'):
            yield
    finally:
        frappe.flags.pulse_approval_action = previous


def _notify(user, task, message):
    if not frappe.db.get_value('User', user, 'enabled') or not frappe.has_permission('Task', 'read', doc=task, user=user):
        return
    frappe.get_doc({'doctype': 'Pulse Notification', 'recipient': user, 'notification_type': 'System',
        'reference_doctype': 'Task', 'reference_name': task.name,
        'message': message + ': ' + task.subject, 'link_url': '/pulse/board?project=' + quote(task.project, safe='') + '&task=' + quote(task.name, safe='')}).insert(ignore_permissions=True)
    frappe.publish_realtime('pulse_notification', {'refresh': True}, user=user, after_commit=True)
    from pulse.api.notify import _email
    _email(user, message, task.subject)


@frappe.whitelist()
def get_approvals(task):
    doc = require_permission('Task', task)
    current = content_hash(doc)
    rows = frappe.get_all('Pulse Task Approval', filters={'task': doc.name},
        fields=['name', 'requested_by', 'reviewer', 'decision', 'note', 'decided_by', 'decided_at', 'creation', 'content_hash'],
        order_by='creation desc', limit_page_length=0)
    for row in rows:
        row['current'] = row.pop('content_hash') == current
        row['can_decide'] = row['current'] and row['decision'] == 'Pending' and row['reviewer'] == frappe.session.user and frappe.has_permission('Task', 'write', doc=doc)
    reviewers = []
    if frappe.has_permission('Task', 'write', doc=doc):
        reviewers = [user for user in frappe.get_all('User', filters={'enabled': 1, 'user_type': 'System User'}, fields=['name', 'full_name'], limit_page_length=0)
            if user.name not in {'Guest', frappe.session.user} and frappe.has_permission('Task', 'write', doc=doc, user=user.name)]
    return {'approvals': rows, 'reviewers': reviewers, 'can_request': frappe.has_permission('Task', 'write', doc=doc)}


@frappe.whitelist(methods=['POST'])
def request_approval(task, reviewer):
    if not isinstance(reviewer, str) or not reviewer.strip():
        frappe.throw('Provide an exact reviewer user ID.')
    doc = require_permission('Task', task, 'write')
    if not doc.project:
        frappe.throw('Select a project before requesting approval.')
    frappe.db.sql('SELECT name FROM `tabTask` WHERE name=%s FOR UPDATE', (doc.name,))
    doc.reload()
    doc.check_permission('write')
    if reviewer == frappe.session.user or not frappe.db.get_value('User', reviewer, 'enabled') or frappe.db.get_value('User', reviewer, 'user_type') != 'System User' or not frappe.has_permission('Task', 'write', doc=doc, user=reviewer):
        frappe.throw('Choose another enabled reviewer with write access to this task.', frappe.PermissionError)
    version = content_hash(doc)
    existing = frappe.db.get_value('Pulse Task Approval', {'task': doc.name, 'reviewer': reviewer,
        'content_hash': version, 'decision': 'Pending'}, 'name')
    if existing:
        return {'name': existing}
    with _action():
        approval = frappe.get_doc({'doctype': 'Pulse Task Approval', 'task': doc.name, 'project': doc.project,
            'requested_by': frappe.session.user, 'reviewer': reviewer, 'content_hash': version, 'decision': 'Pending'}).insert(ignore_permissions=True)
        _notify(reviewer, doc, 'Task approval requested')
    return {'name': approval.name}


@frappe.whitelist(methods=['POST'])
def decide(name, decision, note=''):
    if not isinstance(name, str) or not name.strip():
        frappe.throw('Provide an exact approval ID.')
    approval = frappe.get_doc('Pulse Task Approval', name)
    task = require_permission('Task', approval.task, 'write')
    frappe.db.sql('SELECT name FROM `tabTask` WHERE name=%s FOR UPDATE', (task.name,))
    task.reload()
    task.check_permission('write')
    frappe.db.sql('SELECT name FROM `tabPulse Task Approval` WHERE name=%s FOR UPDATE', (name,))
    approval.reload()
    if not frappe.db.get_value('User', frappe.session.user, 'enabled') or approval.reviewer != frappe.session.user or approval.requested_by == frappe.session.user:
        frappe.throw('Only the assigned reviewer may decide this approval.', frappe.PermissionError)
    if approval.decision != 'Pending':
        frappe.throw('This approval has already been decided.')
    if content_hash(task) != approval.content_hash:
        frappe.throw('Task content changed. Request a new approval for the current version.')
    if not isinstance(decision, str) or decision not in {'Approved', 'Rejected'} or not isinstance(note, str) or len(note) > 5000:
        frappe.throw('Choose Approved or Rejected and use a note of at most 5000 characters.')
    with _action():
        approval.update({'decision': decision, 'note': note, 'decided_by': frappe.session.user, 'decided_at': now_datetime()})
        approval.save(ignore_permissions=True)
        _notify(approval.requested_by, task, 'Task ' + decision.lower())
    return {'name': approval.name, 'decision': approval.decision}
