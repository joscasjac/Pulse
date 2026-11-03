"""Idempotent commercial handoffs; native Project and Task remain canonical."""
import hashlib
import frappe
from pulse.hooks.permissions import require_permission

SOURCES = {'Sales Order', 'CRM Deal', 'Opportunity'}


def _source(doctype, name):
    if not isinstance(doctype, str) or doctype not in SOURCES:
        frappe.throw('Choose a Sales Order, CRM Deal or Opportunity.')
    if not isinstance(name, str) or not name.strip() or len(name) > 140:
        frappe.throw('Provide an exact source record ID.')
    doc = require_permission(doctype, name)
    if doc.get('docstatus') == 2:
        frappe.throw('Cancelled records cannot be handed off.')
    if doctype == 'Sales Order' and doc.docstatus != 1:
        frappe.throw('Submit the sales order before creating delivery work.')
    return doc


def _identity(doctype, name):
    return 'pulse-handoff-' + hashlib.sha256((doctype + ':' + name).encode()).hexdigest()


@frappe.whitelist()
def existing(source_doctype, source_name):
    _source(source_doctype, source_name)
    project = frappe.db.get_value('Pulse Business Handoff', _identity(source_doctype, source_name), 'project')
    if project:
        require_permission('Project', project)
    return {'project': project}


@frappe.whitelist(methods=['POST'])
def create(source_doctype, source_name, project_name, template=None):
    source = _source(source_doctype, source_name)
    if template is not None and (not isinstance(template, str) or not template.strip() or len(template) > 140):
        frappe.throw('Provide an exact template project ID.')
    if not isinstance(project_name, str) or not project_name.strip():
        frappe.throw('Enter a project name.')
    if not frappe.has_permission('Project', 'create'):
        frappe.throw('Project creation is not permitted.', frappe.PermissionError)
    # The source row serializes all handoffs for this stable source identity,
    # including simultaneous automation retries with different request IDs.
    frappe.db.sql(f'SELECT name FROM `tab{source_doctype}` WHERE name=%s FOR UPDATE', source.name)
    key = _identity(source_doctype, source_name)
    project = frappe.db.get_value('Pulse Business Handoff', key, 'project')
    if project:
        require_permission('Project', project)
        return {'project': project, 'created': False}
    linked_project = source.get('project') if source_doctype == 'Sales Order' else None
    if source_doctype == 'Sales Order' and not linked_project:
        matches = frappe.get_all('Project', filters={'sales_order': source.name}, pluck='name', limit_page_length=2)
        if len(matches) > 1:
            frappe.throw('This order has multiple delivery projects. Review its native project links before starting a handoff.')
        linked_project = matches[0] if matches else None
    if linked_project:
        require_permission('Project', linked_project)
        frappe.get_doc({'doctype': 'Pulse Business Handoff', 'source_doctype': source_doctype,
            'source_name': source_name, 'project': linked_project}).insert(ignore_permissions=True, set_name=key)
        return {'project': linked_project, 'created': False}
    customer = source.get('customer') if source_doctype == 'Sales Order' else None
    order = source.name if source_doctype == 'Sales Order' else None
    from pulse.services.atomic import atomic_scope
    with atomic_scope('handoff'):
        if template:
            from pulse.api.business import clone_template
            result = clone_template(template, project_name, customer=customer, sales_order=order)
            project = result['project']
        else:
            fields = {'doctype': 'Project', 'project_name': project_name.strip(), 'customer': customer, 'sales_order': order}
            if source.get('company'):
                fields['company'] = source.company
            project = frappe.get_doc(fields).insert().name
        frappe.get_doc({'doctype': 'Pulse Business Handoff', 'source_doctype': source_doctype,
            'source_name': source_name, 'project': project}).insert(ignore_permissions=True, set_name=key)
    return {'project': project, 'created': True}
