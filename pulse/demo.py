"""Opt-in, native-record demo dataset for isolated evaluation sites."""
import frappe
from frappe.utils import add_days, today, cint

TITLE = 'Pulse Demo — Delivery'
MARKER = 'Pulse demo dataset v1. Synthetic evaluation data; no customer, users or email recipients.'
TASKS = [('Plan delivery', 'To Do', 'High'), ('Prepare a shared review', 'In Progress', 'Medium'), ('Publish the handoff notes', 'Done', 'Low')]


def seed():
    """Run using bench execute; refuses sites without pulse_demo_mode enabled."""
    if cint(frappe.conf.get('pulse_demo_mode')) != 1:
        frappe.throw('Demo generation is disabled. Enable pulse_demo_mode only on a disposable evaluation site.')
    if frappe.session.user != 'Administrator':
        frappe.throw('Demo generation requires Administrator.', frappe.PermissionError)
    with frappe.cache.lock('pulse_demo_seed', timeout=60, blocking_timeout=5):
        return _seed()


def _seed():
    existing = frappe.db.get_value('Project', {'project_name': TITLE}, ['name', 'notes'], as_dict=True)
    if existing and existing.notes != MARKER:
        frappe.throw('A project already uses the demo name. Refusing to modify unrecognized data.')
    from pulse.services.atomic import atomic_scope
    with atomic_scope('pulse_demo'):
        project = frappe.get_doc('Project', existing.name) if existing else frappe.get_doc({
            'doctype': 'Project', 'project_name': TITLE, 'notes': MARKER}).insert()
        tasks = []
        for index, (subject, state, priority) in enumerate(TASKS):
            name = frappe.db.get_value('Task', {'project': project.name, 'subject': subject}, 'name')
            if not name:
                name = frappe.get_doc({'doctype': 'Task', 'project': project.name, 'subject': subject,
                    'description': '<p>Synthetic demo task. Use it to explore list, board, calendar and timeline views.</p>',
                    'workflow_state': state, 'priority': priority, 'exp_start_date': today(),
                    'exp_end_date': add_days(today(), index + 2)}).insert().name
            tasks.append(name)
        if not frappe.db.exists('Pulse Checklist', {'task': tasks[0], 'item': 'Confirm the delivery scope'}):
            frappe.get_doc({'doctype': 'Pulse Checklist', 'task': tasks[0], 'item': 'Confirm the delivery scope'}).insert()
        from pulse.api import modules
        module = frappe.db.get_value('Pulse Module', {'project': project.name, 'title': 'Demo delivery'}, 'name')
        if not module:
            module = modules.save_module(project=project.name, title='Demo delivery')['name']
        modules.set_tasks(module, tasks)
        return {'project': project.name, 'tasks': tasks, 'module': module, 'synthetic': True}
