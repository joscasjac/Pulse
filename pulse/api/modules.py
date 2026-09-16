"""Project modules are groupings of native Tasks, with permission-scoped progress."""
import frappe
from pulse.hooks.permissions import require_permission, scoped_has_permission


def _visible_names(doctype, user):
    if not frappe.has_permission(doctype, 'read', user=user):
        return 'NULL'
    names = frappe.get_list(doctype, pluck='name', limit_page_length=0, user=user)
    return ','.join(frappe.db.escape(name) for name in names) or 'NULL'


def query_conditions(user=None):
    user = user or frappe.session.user
    return '`tabPulse Module`.`project` IN (' + _visible_names('Project', user) + ')'


def has_permission(doc, user=None, **kwargs):
    return scoped_has_permission(doc, user, ptype=kwargs.get('ptype'), permission_type=kwargs.get('permission_type'))


def membership_query(user=None):
    user = user or frappe.session.user
    return ('`tabPulse Module Task`.`module` IN (' + _visible_names('Pulse Module', user) + ')'
            ' AND `tabPulse Module Task`.`task` IN (' + _visible_names('Task', user) + ')')


def membership_permission(doc, user=None, **kwargs):
    user = user or frappe.session.user
    return (scoped_has_permission(doc, user, ptype=kwargs.get('ptype'), permission_type=kwargs.get('permission_type'))
            and frappe.has_permission('Pulse Module', 'read', doc=doc.module, user=user)
            and frappe.has_permission('Task', 'read', doc=doc.task, user=user))


def _tasks(name):
    links = frappe.get_list('Pulse Module Task', filters={'module': name}, pluck='task', limit_page_length=0)
    if not links:
        return []
    return frappe.get_list('Task', filters={'name': ['in', links], 'project': frappe.db.get_value('Pulse Module',name,'project'), 'pulse_archived': 0, 'status': ['!=', 'Cancelled']}, fields=['name','issue_key','subject','status','workflow_state','priority','project','exp_start_date','exp_end_date','_assign'], limit_page_length=0, order_by='pulse_rank asc, modified desc')


def _summary(doc):
    tasks = _tasks(doc.name)
    complete = sum(t.status == 'Completed' for t in tasks)
    return dict(name=doc.name, title=doc.title, module_name=doc.title, project=doc.project, description=doc.description, status=doc.status, start_date=doc.start_date, due_date=doc.due_date, lead=doc.lead, total=len(tasks), completed=complete, percentage=round(100*complete/len(tasks)) if tasks else 0, can_write=frappe.has_permission('Pulse Module','write',doc=doc))


@frappe.whitelist()
def list_modules(project):
    require_permission('Project',project)
    return [_summary(frappe.get_doc('Pulse Module', r.name)) for r in frappe.get_list('Pulse Module',filters={'project':project},fields=['name'],order_by='title asc',limit_page_length=0)]


@frappe.whitelist()
def get_module(name):
    doc = require_permission('Pulse Module',name)
    return dict(_summary(doc), tasks=_tasks(name))


@frappe.whitelist()
def save_module(project, title, name=None, description='', status='Backlog', start_date=None, due_date=None, lead=None):
    require_permission('Project',project)
    doc = require_permission('Pulse Module', name, 'write') if name else frappe.new_doc('Pulse Module')
    doc.update(dict(project=project,title=title,description=description,status=status,start_date=start_date or None,due_date=due_date or None,lead=lead or None))
    doc.save()
    return get_module(doc.name)


@frappe.whitelist()
def set_tasks(name,tasks,remove=0):
    module = require_permission('Pulse Module', name,'write')
    tasks = frappe.parse_json(tasks) if isinstance(tasks,str) else tasks
    if (not isinstance(tasks,list) or len(tasks)>500
            or any(not isinstance(task, str) or not task for task in tasks)):
        frappe.throw('Select up to 500 tasks.')
    tasks = list(dict.fromkeys(tasks))
    for task in tasks:
        if require_permission('Task',task,'write').project != module.project:
            frappe.throw('Tasks must belong to this module’s project.')
    savepoint = 'pulse_module_' + frappe.generate_hash(length=10)
    frappe.db.savepoint(savepoint)
    try:
        frappe.db.sql('SELECT name FROM `tabPulse Module` WHERE name=%s FOR UPDATE',(name,))
        for task in tasks:
            existing = frappe.db.get_value('Pulse Module Task',{'module':name,'task':task},'name',for_update=True)
            if str(remove).lower() in ('1','true'):
                if existing:
                    frappe.delete_doc('Pulse Module Task',existing)
            elif not existing:
                frappe.get_doc(dict(doctype='Pulse Module Task',module=name,task=task,project=module.project)).insert()
        return get_module(name)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise



@frappe.whitelist()
def task_modules(task):
    doc = require_permission('Task',task)
    if not doc.project:
        return {'modules':[], 'available':[]}
    available = list_modules(doc.project)
    linked = set(frappe.get_list('Pulse Module Task',filters={'task':task},pluck='module',limit_page_length=0))
    return {'modules':[m for m in available if m['name'] in linked], 'available':[m for m in available if m['name'] not in linked]}


@frappe.whitelist()
def available_tasks(name):
    doc = require_permission('Pulse Module',name)
    linked = set(frappe.get_list('Pulse Module Task',filters={'module':name},pluck='task',limit_page_length=0))
    return [r for r in frappe.get_list('Task',filters={'project':doc.project,'pulse_archived':0},fields=['name','issue_key','subject','workflow_state'],limit_page_length=0,order_by='modified desc') if r.name not in linked and frappe.has_permission('Task','write',doc=r.name)]


def modules_for_tasks(names):
    """Only expose module metadata readable to the current task viewer."""
    result = {name: [] for name in names}
    if not names:
        return result
    for row in frappe.get_list('Pulse Module Task', filters={'task':['in',names]}, fields=['task','module'], limit_page_length=0):
        if frappe.has_permission('Pulse Module','read',doc=row.module):
            module = frappe.get_doc('Pulse Module',row.module)
            if frappe.db.get_value('Task',row.task,'project') == module.project:
                result[row.task].append({'name':module.name,'title':module.title})
    return result


def task_project_changed(doc, method=None):
    """Membership is project-bound; moving the native task removes old memberships."""
    old = doc.get_doc_before_save()
    if old and old.project != doc.project and frappe.db.table_exists('Pulse Module Task'):
        # System integrity cleanup in the task save transaction, including links
        # the mover may no longer read after leaving the source project.
        frappe.db.delete('Pulse Module Task', {'task':doc.name})


def task_deleted(doc, method=None):
    if frappe.db.table_exists('Pulse Module Task'):
        frappe.db.delete('Pulse Module Task', {'task':doc.name})
