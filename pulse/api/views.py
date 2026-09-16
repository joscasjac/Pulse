"""Permission-filtered cross-project work views and private layout preferences."""
import json
import hashlib
from datetime import date as calendar_date, timedelta
import frappe
from pulse.hooks.permissions import require_permission
from pulse.services.view_filters import validate_filter, matches, FIELDS


def configuration(value):
    data = frappe.parse_json(value) if isinstance(value, str) else value
    data = data or {}
    if not isinstance(data, dict):
        frappe.throw('View configuration must be an object.')
    tree = data.get('filter', {'op': 'and', 'rules': []})
    try:
        validate_filter(tree)
    except ValueError as exc:
        frappe.throw(str(exc))
    columns = data.get('columns', ['subject', 'workflow_state', 'priority', 'project', 'exp_start_date', 'exp_end_date'])
    if not isinstance(columns, list) or not columns or any(not isinstance(c, str) for c in columns) or len(columns) != len(set(columns)) or any(c not in FIELDS | {'modules'} for c in columns):
        frappe.throw('Choose distinct supported columns.')
    if data.get('layout', 'spreadsheet') not in ('spreadsheet', 'calendar', 'timeline'):
        frappe.throw('Unknown layout.')
    if data.get('group', '') not in ('', 'workflow_state', 'assignees', 'priority', 'project', 'labels'):
        frappe.throw('Unknown grouping.')
    hide_weekends = data.get('hide_weekends', True)
    if hide_weekends not in (True, False, 0, 1):
        frappe.throw('Hide weekends must be a boolean.')
    order_by = data.get('order_by', 'pulse_rank')
    if order_by not in FIELDS | {'pulse_rank', 'creation', 'modified', 'owner', 'name'}:
        frappe.throw('Choose a supported sort property.')
    direction = data.get('order_direction', 'asc')
    if direction not in ('asc', 'desc'):
        frappe.throw('Choose ascending or descending order.')
    show_subtasks = data.get('show_subtasks', True)
    if show_subtasks not in (True, False, 0, 1):
        frappe.throw('Show subtasks must be a boolean.')
    calendar_layout = data.get('calendar_layout', 'month')
    if calendar_layout not in ('month', 'week'):
        frappe.throw('Choose month or week calendar layout.')
    return {'calendar_layout': calendar_layout, 'order_by': order_by, 'order_direction': direction, 'show_subtasks': bool(show_subtasks), 'hide_weekends': bool(hide_weekends), 'filter': tree, 'columns': columns, 'layout': data.get('layout', 'spreadsheet'), 'group': data.get('group', '')}


@frappe.whitelist()
def tasks(config=None, include_archived=0):
    settings = configuration(config)
    # get_list always applies native role, user and Pulse row permissions.
    rows = frappe.get_list('Task', filters={} if str(include_archived).lower() in ('1', 'true') else {'pulse_archived': 0}, fields=['name', 'issue_key', 'subject', 'status', 'workflow_state', 'priority', 'type', 'project', 'exp_start_date', 'exp_end_date', 'expected_time', 'pulse_story_points', '_assign', 'creation', 'modified', 'owner', 'pulse_rank', 'parent_task'], limit_page_length=0, order_by='exp_end_date asc, name asc')
    names = [r.name for r in rows]
    labels = {}
    if names:
        for r in frappe.get_all('Pulse Task Label', filters={'parent': ['in', names], 'parenttype': 'Task'}, fields=['parent', 'label']):
            labels.setdefault(r.parent, []).append(r.label)
    for row in rows:
        row['assignees'] = frappe.parse_json(row.pop('_assign', None) or '[]')
        row['labels'] = labels.get(row.name, [])
        row['can_write'] = frappe.has_permission('Task', 'write', doc=row.name)
    result = [r for r in rows if matches(r, settings['filter'])]
    from pulse.api.modules import modules_for_tasks
    memberships = modules_for_tasks([r.name for r in result])
    for row in result:
        row['modules'] = memberships.get(row.name, [])
    visible = {r.name for r in result}
    return {'tasks': result, 'dependencies': _visible_dependencies(visible)}


# Preserve the internal import used by existing view consumers.
from pulse.services.dependencies import visible_dependencies as _visible_dependencies


@frappe.whitelist(methods=['POST'])
def schedule_tasks(tasks, date, module=None):
    """Schedule every selected task atomically, keeping each task's duration."""
    names = frappe.parse_json(tasks) if isinstance(tasks, str) else tasks
    if not isinstance(names, list) or not names or len(names) > 200 or any(not isinstance(name, str) or not name for name in names):
        frappe.throw('Select between 1 and 200 tasks.')
    try:
        due = calendar_date.fromisoformat(date)
    except (ValueError, TypeError):
        frappe.throw('Choose a valid date in YYYY-MM-DD format.')
    names = list(dict.fromkeys(names))
    # Do not touch a readable task before discovering a denied task later in the list.
    docs = [require_permission('Task', name, 'write') for name in names]
    if module:
        module_doc = require_permission('Pulse Module', module, 'write')
        if any(doc.project != module_doc.project for doc in docs):
            frappe.throw('Tasks must belong to this module’s project.')
    from frappe.utils import getdate
    savepoint = 'pulse_schedule_' + frappe.generate_hash(length=10)
    frappe.db.savepoint(savepoint)
    try:
        if module:
            from pulse.api.modules import set_tasks
            set_tasks(module, names)
        for doc in docs:
            if doc.exp_start_date:
                duration = max(0, (getdate(doc.exp_end_date) - getdate(doc.exp_start_date)).days) if doc.exp_end_date else 0
                doc.exp_start_date = due - timedelta(days=duration)
            doc.exp_end_date = due
            doc.save()
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
    frappe.publish_realtime('pulse:board', {}, after_commit=True)
    return {'updated': names, 'count': len(names), 'date': due.isoformat()}


@frappe.whitelist()
def saved_views():
    rows = frappe.get_list('Pulse Saved View', fields=['name', 'title', 'owner', 'shared', 'configuration'], limit_page_length=0, order_by='title asc')
    for row in rows:
        row['can_write'] = row.owner == frappe.session.user
    return rows


@frappe.whitelist()
def save_view(title, config, shared=0, name=None):
    doc = require_permission('Pulse Saved View', name, 'write') if name else frappe.new_doc('Pulse Saved View')
    doc.update({'title': title, 'configuration': json.dumps(configuration(config)), 'shared': int(shared)})
    doc.save()
    return doc.as_dict()


def workspace_configuration(value):
    data = frappe.parse_json(value) if isinstance(value, str) else value
    data = data or {}
    if not isinstance(data, dict):
        frappe.throw('Workspace preferences must be an object.')
    layout = data.get('layout', 'list')
    if layout not in ('list', 'board', 'calendar', 'timeline', 'spreadsheet'):
        frappe.throw('Unknown workspace layout.')
    filters = data.get('filters', {})
    if not isinstance(filters, dict):
        frappe.throw('Workspace filters must be an object.')
    normalized = {}
    for field in ('q', 'type', 'priority', 'assignee'):
        value = filters.get(field, '')
        if not isinstance(value, str) or len(value) > 500:
            frappe.throw('Filter values must be text of at most 500 characters.')
        normalized[field] = value
    flags = {}
    for key in ('include_archived', 'filters_open', 'display_open'):
        value = data.get(key, False)
        if value not in (True, False, 0, 1):
            frappe.throw('Display preferences must be booleans.')
        flags[key] = bool(value)
    return {'layout': layout, 'filters': normalized, **flags}


@frappe.whitelist()
def preferences(config=None, context=None):
    # Every key remains private to the signed-in user. Context separates projects
    # and the task workspace from saved-view editors without changing legacy keys.
    if context is not None and (not isinstance(context, str) or not context or len(context) > 180):
        frappe.throw('Preference context must be text of at most 180 characters.')
    key = 'pulse_work_view' if context is None else 'pulse_view_' + hashlib.sha256(context.encode()).hexdigest()[:32]
    normalize = workspace_configuration if context and context.startswith('board:') else configuration
    if config is not None:
        value = json.dumps(normalize(config))
        frappe.defaults.set_user_default(key, value)
        return json.loads(value)
    return normalize(frappe.defaults.get_user_default(key))


def query_conditions(user=None):
    user = user or frappe.session.user
    return f'(`tabPulse Saved View`.owner = {frappe.db.escape(user)} OR `tabPulse Saved View`.shared = 1)'


def has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    action = permission_type or ptype or 'read'
    owner = frappe.db.get_value('Pulse Saved View', doc.name, 'owner') if not doc.is_new() else doc.owner
    return bool(owner == user or (doc.shared and action == 'read'))
