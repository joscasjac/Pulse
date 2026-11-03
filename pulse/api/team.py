"""Project membership and assignment handoff over native ERPNext records."""
import frappe
from pulse.hooks.permissions import require_permission
from pulse.services.atomic import atomic_scope


def _project(project, lock=False):
    if frappe.session.user != 'Administrator' and not set(frappe.get_roles()) & {'System Manager', 'Pulse Admin'}:
        frappe.throw('Project team administration requires Pulse Admin or System Manager.', frappe.PermissionError)
    doc = frappe.get_doc('Project', project, for_update=lock)
    doc.check_permission('write')
    return doc


def _user(user, lock=False, allow_website=False):
    record = frappe.get_doc('User', user, for_update=lock)
    if record.name in ('Guest', 'Administrator') or not record.enabled or (record.user_type != 'System User' and not (allow_website and record.user_type == 'Website User')):
        frappe.throw('Choose an enabled system user.')
    return record


@frappe.whitelist()
def get_team(project):
    doc = _project(project)
    return {'project': doc.name, 'owner': doc.owner,
            'can_manage_accounts': frappe.session.user == 'Administrator' or 'System Manager' in frappe.get_roles(),
            'members': [{'user': row.user, 'full_name': row.full_name or row.user}
                        for row in doc.users],
            'offboarding_candidates': frappe.get_all('User', filters={'enabled': 1, 'name': ['not in', ['Guest', 'Administrator']]},
                fields=['name', 'full_name', 'user_type'], order_by='full_name asc', limit_page_length=0)
                if frappe.session.user == 'Administrator' or 'System Manager' in frappe.get_roles() else [],
            'candidates': frappe.get_all('User', filters={'enabled': 1, 'user_type': 'System User',
                'name': ['not in', ['Guest', 'Administrator']]}, fields=['name', 'full_name'],
                order_by='full_name asc', limit_page_length=0)}


@frappe.whitelist(methods=['POST'])
def add_member(project, user):
    doc = _project(project, lock=True)
    _user(user)
    if not any(row.user == user for row in doc.users):
        with atomic_scope('pulse_add_member'):
            doc.append('users', {'user': user})
            doc.save()
    return get_team(project)


@frappe.whitelist(methods=['POST'])
def remove_member(project, user, replacement=None):
    """Remove project membership and hand off open assignments in one transaction.

    This does not disable the ERP account. Native Project saves revoke project
    shares; separate task shares may still provide access.
    The creator must transfer project ownership before removing themselves.
    """
    doc = _project(project, lock=True)
    if user == doc.owner:
        frappe.throw('Transfer project ownership before removing its owner.')
    if not any(row.user == user for row in doc.users):
        frappe.throw('This user is not a project member.')
    if replacement:
        _user(replacement)
        if replacement == user or not any(row.user == replacement for row in doc.users):
            frappe.throw('Choose another existing project member for the handoff.')
    # Administrators still need native Task write permission for every affected task.
    task_names = frappe.get_all('Task', filters={'project': project}, pluck='name', limit_page_length=0)
    assigned = frappe.get_all('ToDo', filters={'reference_type': 'Task',
        'reference_name': ['in', task_names], 'allocated_to': user, 'status': 'Open'},
        pluck='reference_name', limit_page_length=0) if task_names else []
    assigned = list(dict.fromkeys(assigned))
    for name in assigned:
        require_permission('Task', name, 'write')
    with atomic_scope('pulse_team'):
        from pulse.api.tasks import bulk_update
        for offset in range(0, len(assigned), 200):
            bulk_update(assigned[offset:offset + 200], unassign=[user],
                        assign=[replacement] if replacement else [])
        doc.set('users', [row for row in doc.users if row.user != user])
        doc.save()
    return {'removed': user, 'reassigned_to': replacement, 'tasks': assigned}


@frappe.whitelist(methods=['POST'])
def transfer_owner(project, user):
    doc = _project(project, lock=True)
    _user(user)
    if not any(row.user == user for row in doc.users):
        frappe.throw('The new owner must already be a project member.')
    previous = doc.owner
    with atomic_scope('pulse_owner'):
        # owner is a Frappe constant, so this is a narrowly checked admin operation.
        frappe.db.set_value('Project', doc.name, 'owner', user)
        frappe.clear_document_cache('Project', doc.name)
        frappe.get_doc({'doctype': 'Pulse Activity Log', 'user': frappe.session.user,
            'activity_type': 'Project Ownership Changed', 'reference_doctype': 'Project',
            'reference_name': doc.name, 'project': doc.name,
            'description': f'Project ownership transferred from {previous} to {user}'}).insert(ignore_permissions=True)
    return {'project': doc.name, 'previous_owner': previous, 'owner': user}


def _system_manager():
    if frappe.session.user != 'Administrator' and 'System Manager' not in frappe.get_roles():
        frappe.throw('Account invitations and offboarding require System Manager.', frappe.PermissionError)


def _audit_team(description, project=None):
    # Use a supported existing activity type, with an explicit description.
    frappe.get_doc({'doctype': 'Pulse Activity Log', 'user': frappe.session.user,
        'activity_type': 'Assignment Changed', 'reference_doctype': 'Project' if project else None,
        'reference_name': project, 'project': project, 'description': description}).insert(ignore_permissions=True)


@frappe.whitelist(methods=['POST'])
def invite_member(project, email, first_name, last_name=None):
    """Create a minimally privileged native system user and queue its welcome email."""
    _system_manager()
    doc = _project(project, lock=True)
    email = (email or '').strip().lower()
    from frappe.utils import validate_email_address
    validate_email_address(email, throw=True)
    if not (first_name or '').strip():
        frappe.throw('Enter the new member’s first name.')
    if frappe.db.exists('User', email):
        frappe.throw('This account already exists. Add the existing enabled user instead.')
    if not frappe.has_permission('User', 'create'):
        frappe.throw('You cannot create ERP users.', frappe.PermissionError)
    with atomic_scope('pulse_invite'):
        user = frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': first_name.strip(),
            'last_name': (last_name or '').strip(), 'enabled': 1, 'user_type': 'System User',
            'send_welcome_email': 0, 'roles': [{'role': 'Projects User'}, {'role': 'Pulse Junior Developer'}]}).insert()
        doc.append('users', {'user': user.name, 'welcome_email_sent': 1})
        doc.save()
        _audit_team(f'Invited {user.name} with Projects User and Pulse Junior Developer roles', doc.name)
        # User.insert catches outgoing-mail errors. An explicit native welcome call
        # propagates failures so this endpoint never reports a nonexistent invite.
        user.flags.delay_emails = True
        user.send_welcome_mail_to_user()
        result = {'user': user.name, 'welcome_email_queued': True, 'team': get_team(project)}
    return result


def _offboarding_plan(user, replacement, lock=False):
    import hashlib
    _system_manager()
    target = _user(user, lock=lock, allow_website=True)
    target.check_permission('write')
    user = target.name
    if user == frappe.session.user:
        frappe.throw('You cannot offboard your own account.')
    if replacement == user or not replacement:
        frappe.throw('Choose another enabled user to receive the work.')
    replacement_doc = _user(replacement, lock=lock)
    replacement = replacement_doc.name
    if replacement == user:
        frappe.throw('Choose another enabled user to receive the work.')
    if 'System Manager' in frappe.get_roles(user):
        frappe.throw('Remove System Manager privileges through ERP user administration before offboarding this account.')
    if lock:
        # Current locking reads avoid a stale MariaDB repeatable-read snapshot after
        # waiting for a concurrent assignment's User lock. Values are bound parameters.
        memberships = frappe.db.sql('SELECT parent FROM `tabProject User` WHERE user=%s AND parenttype=%s FOR UPDATE',
                                    (user, 'Project'), as_dict=True)
        owned = frappe.db.sql('SELECT name FROM `tabProject` WHERE owner=%s FOR UPDATE', (user,), as_dict=True)
        project_names = sorted({row.parent for row in memberships} | {row.name for row in owned})
    else:
        project_names = sorted(set(frappe.get_all('Project User', filters={'user': user, 'parenttype': 'Project'}, pluck='parent', limit_page_length=0)) |
                               set(frappe.get_all('Project', filters={'owner': user}, pluck='name', limit_page_length=0)))
    projects = []
    for name in project_names:
        doc = _project(name, lock=lock)
        projects.append({'name': name, 'project_name': doc.project_name, 'owner': doc.owner,
                         'modified': str(doc.modified), 'replacement_is_member': any(r.user == replacement for r in doc.users)})
    if lock:
        assignments = frappe.db.sql('SELECT name, reference_type, reference_name, description, modified FROM `tabToDo` WHERE allocated_to=%s AND status=%s ORDER BY name ASC FOR UPDATE',
                                    (user, 'Open'), as_dict=True)
    else:
        assignments = frappe.get_all('ToDo', filters={'allocated_to': user, 'status': 'Open'},
            fields=['name', 'reference_type', 'reference_name', 'description', 'modified'], limit_page_length=0, order_by='name asc')
    for row in assignments:
        require_permission('ToDo', row.name, 'write')
        if row.reference_type and row.reference_name:
            require_permission(row.reference_type, row.reference_name, 'write')
        row.modified = str(row.modified)
    if lock:
        shares = frappe.db.sql('SELECT name, share_doctype, share_name, modified FROM `tabDocShare` WHERE user=%s ORDER BY name ASC FOR UPDATE',
                               (user,), as_dict=True)
    else:
        shares = frappe.get_all('DocShare', filters={'user': user}, fields=['name', 'share_doctype', 'share_name', 'modified'],
                                limit_page_length=0, order_by='name asc')
    for row in shares:
        require_permission(row.share_doctype, row.share_name, 'share')
        row.modified = str(row.modified)
    external_grants = []
    if frappe.db.exists('DocType', 'Pulse External Share'):
        if lock:
            external_grants = frappe.db.sql('SELECT name, task, modified FROM `tabPulse External Share` WHERE user=%s AND enabled=1 ORDER BY name ASC FOR UPDATE', (user,), as_dict=True)
        else:
            external_grants = frappe.get_all('Pulse External Share', filters={'user': user, 'enabled': 1},
                fields=['name', 'task', 'modified'], order_by='name asc', limit_page_length=0)
        for grant in external_grants:
            require_permission('Task', grant.task, 'write')
            grant.modified = str(grant.modified)
    plan = {'user': user, 'replacement': replacement, 'user_modified': str(target.modified), 'replacement_modified': str(replacement_doc.modified),
            'projects': projects, 'assignments': assignments, 'shares': shares, 'external_grants': external_grants,
            'effects': ['Transfer owned projects', 'Replace project membership', 'Hand off all open ERP assignments',
                        'Remove direct record shares and external portal grants', 'Disable the ERP account and end its sessions']}
    plan['preview_token'] = hashlib.sha256(frappe.as_json(plan).encode()).hexdigest()
    return plan


@frappe.whitelist()
def preview_offboarding(user, replacement):
    return _offboarding_plan(user, replacement)


@frappe.whitelist(methods=['POST'])
def offboard_user(user, replacement, preview_token):
    """Apply the reviewed organization-wide plan atomically; never delete the account."""
    _system_manager()
    if not isinstance(user, str) or not isinstance(replacement, str) or not user or not replacement:
        frappe.throw('Choose the departing user and a replacement.')
    # Match the native assignment hook lock before collecting the final scope.
    for account_name in sorted({user, replacement}):
        frappe.db.get_value('User', account_name, 'enabled', for_update=True)
    plan = _offboarding_plan(user, replacement, lock=True)
    user, replacement = plan['user'], plan['replacement']
    if not preview_token or preview_token != plan['preview_token']:
        frappe.throw('The offboarding plan changed. Review a fresh preview before continuing.')
    with atomic_scope('pulse_offboard'):
        # Add replacement membership before assignment, respecting assignment hierarchy.
        for row in plan['projects']:
            add_member(row['name'], replacement)
            if row['owner'] == user:
                transfer_owner(row['name'], replacement)
        from frappe.desk.form.assign_to import add, remove
        for row in plan['assignments']:
            if row['reference_type'] and row['reference_name']:
                remove(row['reference_type'], row['reference_name'], user)
                add({'doctype': row['reference_type'], 'name': row['reference_name'], 'assign_to': [replacement]})
            else:
                todo = require_permission('ToDo', row['name'], 'write')
                todo.allocated_to = replacement
                todo.save()
        for row in plan['projects']:
            doc = _project(row['name'], lock=True)
            doc.set('users', [member for member in doc.users if member.user != user])
            doc.save()
        from frappe.share import remove as remove_share
        for row in plan['shares']:
            remove_share(row['share_doctype'], row['share_name'], user)
        for grant in plan['external_grants']:
            share = frappe.get_doc('Pulse External Share', grant['name'])
            share.enabled = 0
            share.save(ignore_permissions=True)
        account = require_permission('User', user, 'write')
        _audit_team(f'Offboarded {user}; handed work to {replacement}; disabled ERP account')
        account.enabled = 0
        # Native User validation logs out sessions immediately and can commit.
        # Defer that one effect until the atomic handoff has committed.
        login_manager = getattr(frappe.local, 'login_manager', None)
        try:
            frappe.local.login_manager = None
            account.save()
        finally:
            frappe.local.login_manager = login_manager
        # Worker/API contexts may not have a LoginManager. Native User validation
        # logs out web sessions; this also covers session cleanup after a job commit.
        from functools import partial
        frappe.db.after_commit.add(partial(_clear_offboard_sessions, user=user, force=True))
    return {'user': user, 'disabled': True, 'replacement': replacement,
            'projects_updated': len(plan['projects']), 'assignments_updated': len(plan['assignments']),
            'shares_removed': len(plan['shares']), 'external_grants_revoked': len(plan['external_grants'])}


def _clear_offboard_sessions(user, force=True):
    from frappe.sessions import clear_sessions
    try:
        clear_sessions(user=user, force=force)
    except Exception:
        # Account disablement is already committed; keep this failure observable
        # without making a successful atomic handoff appear to have rolled back.
        frappe.log_error(title='Pulse offboarding session cleanup failed',
                         message=f'Account {user} is disabled. Retry native session cleanup.\n' + frappe.get_traceback())
