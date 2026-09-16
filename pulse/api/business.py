"""Commercial project context, reusable native projects, and capacity planning."""
import json
from datetime import timedelta
import frappe
from frappe.utils import getdate, flt
from pulse.hooks.permissions import require_permission


def _links(customer, sales_order):
    if customer:
        require_permission('Customer', customer)
    if sales_order:
        order = require_permission('Sales Order', sales_order)
        if order.customer != customer:
            frappe.throw('Sales order must belong to the selected customer.')


@frappe.whitelist()
def projects():
    rows = frappe.get_list('Project', fields=['name', 'project_name', 'status', 'notes',
        'pulse_project_key', 'customer', 'sales_order', 'pulse_is_template'], limit_page_length=0)
    for row in rows:
        row.taskCount = len(frappe.get_list('Task', filters={'project': row.name}, pluck='name', limit_page_length=0))
        row.can_write = frappe.has_permission('Project', 'write', doc=row.name)
    return rows


@frappe.whitelist()
def commercial_options(customer=None):
    def options(dt, fields, filters=None):
        if not frappe.has_permission(dt, 'read'):
            return []
        return frappe.get_list(dt, fields=fields, filters=filters or {}, limit_page_length=0)
    return {'customers': options('Customer', ['name', 'customer_name']),
            'orders': options('Sales Order', ['name', 'customer'], {'customer': customer, 'docstatus': ['<', 2]}) if customer else []}


@frappe.whitelist()
def update_project(project, customer=None, sales_order=None, is_template=0):
    doc = require_permission('Project', project, 'write')
    _links(customer, sales_order)
    doc.customer, doc.sales_order = customer or None, sales_order or None
    doc.pulse_is_template = int(is_template or 0)
    doc.save()
    return doc.name


@frappe.whitelist()
def clone_template(template, project_name, customer=None, sales_order=None):
    source = require_permission('Project', template)
    if not source.get('pulse_is_template'):
        frappe.throw('Select a project marked as a template.')
    if not (project_name or '').strip():
        frappe.throw('Enter a project name.')
    _links(customer, sales_order)
    names = frappe.get_list('Task', filters={'project': template}, pluck='name', limit_page_length=0)
    if len(names) != frappe.db.count('Task', {'project': template}):
        frappe.throw('Template creation requires access to every task.', frappe.PermissionError)
    tasks = [require_permission('Task', name) for name in names]
    from pulse.api.task_config import statuses_for, CATEGORY_STATUS
    statuses = statuses_for(source)
    initial = next((row for category in ('To Do', 'Backlog', 'In Progress', 'In Review', 'Blocked')
                    for row in statuses if row['category'] == category), None)
    if tasks and not initial:
        frappe.throw('Add a nonterminal task status to the template before creating a project.')
    labels = frappe.get_list('Pulse Label', filters={'project': template},
                             fields=['name', 'label_name', 'color'], limit_page_length=0)
    # A failed clone must not leave a partially populated project, including callers
    # which catch the exception inside the same request.
    frappe.db.savepoint('pulse_clone')
    try:
        project = frappe.get_doc({'doctype': 'Project', 'project_name': project_name.strip(),
            'company': source.company, 'customer': customer, 'sales_order': sales_order,
            'notes': source.notes,
            'pulse_board_type': source.get('pulse_board_type'),
            'pulse_enable_scrum': source.get('pulse_enable_scrum'),
            'pulse_default_sprint_length': source.get('pulse_default_sprint_length'),
            'pulse_task_statuses': [dict(label=r.label, category=r.category, color=r.color) for r in source.get('pulse_task_statuses') or []],
            'pulse_task_types': [dict(task_type=r.task_type) for r in source.get('pulse_task_types') or []]}).insert()
        label_mapping = {}
        for label in labels:
            copied = frappe.get_doc({'doctype': 'Pulse Label', 'project': project.name,
                'label_name': label.label_name, 'color': label.color}).insert()
            label_mapping[label.name] = copied.name
        mapping = {}
        for task in tasks:
            fields = {key: task.get(key) for key in ('subject', 'description', 'type', 'priority', 'expected_time', 'is_group', 'pulse_story_points')}
            clone = frappe.get_doc({'doctype': 'Task', 'project': project.name, **fields,
                'workflow_state': initial['label'], 'status': CATEGORY_STATUS[initial['category']],
                'pulse_labels': [{'label': label_mapping[row.label]} for row in task.get('pulse_labels') or []]}).insert()
            mapping[task.name] = clone.name
        for task in tasks:
            clone = frappe.get_doc('Task', mapping[task.name])
            clone.parent_task = mapping.get(task.parent_task)
            clone.pulse_epic = mapping.get(task.get('pulse_epic'))
            clone.set('depends_on', [{'task': mapping[row.task]} for row in task.get('depends_on') or [] if row.task in mapping])
            clone.save()
            for item in frappe.get_list('Pulse Checklist', filters={'task': task.name}, fields=['item', 'order_idx'], limit_page_length=0):
                frappe.get_doc({'doctype': 'Pulse Checklist', 'task': clone.name, 'item': item.item, 'order_idx': item.order_idx, 'is_done': 0}).insert()
        if names:
            for dep in frappe.get_list('Pulse Dependency', filters={'source_task': ['in', names]}, fields=['source_task', 'target_task', 'dependency_type', 'lag_days', 'notes'], limit_page_length=0):
                if dep.target_task in mapping:
                    frappe.get_doc({'doctype': 'Pulse Dependency', **dict(dep), 'source_task': mapping[dep.source_task], 'target_task': mapping[dep.target_task], 'status': 'Active'}).insert()
        return {'project': project.name, 'tasks': mapping}
    except Exception:
        frappe.db.rollback(save_point='pulse_clone')
        raise


def capacity_hours(start, end, allocations, leaves):
    """Weekdays × 8h, allocation percentages capped daily, approved leave deduped."""
    hours = 0
    day = getdate(start)
    while day <= getdate(end):
        if day.weekday() < 5 and not any(getdate(r['start_date']) <= day <= getdate(r['end_date']) for r in leaves):
            percent = min(100, sum(max(0, flt(r['allocation_percentage'])) for r in allocations if getdate(r['start_date']) <= day <= getdate(r['end_date'])))
            hours += 8 * percent / 100
        day += timedelta(days=1)
    return round(hours, 2)


@frappe.whitelist()
def workload(start, end, project=None):
    start, end = getdate(start), getdate(end)
    if end < start or (end - start).days > 366:
        frappe.throw('Choose a date range of up to one year.')
    if project:
        require_permission('Project', project)
    live_projects = frappe.get_list('Project', filters={'pulse_is_template': 0}, pluck='name', limit_page_length=0)
    if project and project not in live_projects:
        return {'rows': [], 'unassigned_hours': 0, 'basis': 'Reusable templates are excluded from delivery workload.'}
    filters = {'project': ['in', live_projects], 'status': 'Active', 'start_date': ['<=', end], 'end_date': ['>=', start]}
    if project:
        filters['project'] = project
    allocations = frappe.get_list('Pulse Allocation', filters=filters, fields=['user', 'allocation_percentage', 'start_date', 'end_date'], limit_page_length=0)
    task_filters = {'status': ['not in', ['Completed', 'Cancelled']], 'pulse_archived': 0}
    if project:
        task_filters['project'] = project
    tasks = frappe.get_list('Task', filters=task_filters, fields=['name', 'project', '_assign', 'expected_time', 'exp_start_date', 'exp_end_date'], limit_page_length=0)
    tasks = [task for task in tasks if not task.project or task.project in live_projects]
    people = {r.user for r in allocations}
    estimates, unscheduled = {}, 0
    for task in tasks:
        if task.exp_start_date and getdate(task.exp_start_date) > end or task.exp_end_date and getdate(task.exp_end_date) < start:
            continue
        assignees = json.loads(task._assign or '[]')
        if not assignees:
            unscheduled += flt(task.expected_time)
        for user in assignees:
            people.add(user)
            estimates[user] = estimates.get(user, 0) + flt(task.expected_time) / len(assignees)
    rows = []
    for user in sorted(people):
        # Leave is an availability fact only; never return its reason or record.
        leaves = frappe.get_list('Pulse Leave', filters={'user': user, 'status': 'Approved', 'start_date': ['<=', end], 'end_date': ['>=', start]}, fields=['start_date', 'end_date'], limit_page_length=0)
        available = capacity_hours(start, end, [r for r in allocations if r.user == user], leaves)
        planned = round(estimates.get(user, 0), 2)
        rows.append({'user': user, 'available_hours': available, 'estimated_hours': planned, 'over_hours': round(max(0, planned - available), 2)})
    return {'rows': rows, 'unassigned_hours': round(unscheduled, 2), 'basis': 'Reusable templates excluded. 8-hour weekdays; active allocations; approved leave. Full estimates for open tasks overlapping the period; undated tasks included. Shared assignments split equally.'}


def validate_project_business(doc, method=None):
    if doc.flags.get('ignore_permissions'):
        return
    before = doc.get_doc_before_save()
    if not before or doc.customer != before.customer or doc.sales_order != before.sales_order:
        _links(doc.customer, doc.sales_order)
