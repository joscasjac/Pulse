"""Bounded CSV adoption tools. Native Task validation remains authoritative."""
import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation
import frappe
from pulse.hooks.permissions import require_permission

COLUMNS = ('name', 'subject', 'description', 'priority', 'type', 'exp_start_date',
           'exp_end_date', 'expected_time', 'pulse_story_points')


def _columns(project, permission_type):
    from frappe.model import get_permitted_fields
    from pulse.api.task_config import configurable_fields
    permitted = set(get_permitted_fields('Task', permission_type=permission_type))
    base = [name for name in COLUMNS if name == 'name' or name in permitted]
    configured = {row.fieldname for row in frappe.get_doc('Project', project).get('pulse_task_field_rules') or []}
    custom = [field.fieldname for field in configurable_fields(permission_type)
              if field.fieldname.startswith('custom_') and field.fieldname in configured]
    return tuple(base + sorted(custom))


def _parse(project, content):
    require_permission('Project', project, 'write')
    if not isinstance(content, str) or len(content.encode('utf-8')) > 2_000_000:
        frappe.throw('Choose a UTF-8 CSV file smaller than 2 MB.')
    try:
        reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')), strict=True)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            frappe.throw('CSV headers must be present and unique.')
        if set(reader.fieldnames) - set(_columns(project, 'write')) or 'subject' not in reader.fieldnames:
            frappe.throw('Use the Pulse CSV template headers, including subject.')
        rows = []
        for number, source in enumerate(reader, 2):
            if number > 501:
                frappe.throw('Import at most 500 tasks at a time.')
            if None in source or any(v is None for v in source.values()):
                frappe.throw(f'Row {number} does not match the CSV headers.')
            row = {key: value.strip() for key, value in source.items()}
            for key, value in row.items():
                if value.startswith("''") or (value.startswith("'") and value[1:].lstrip().startswith(('=', '+', '-', '@'))):
                    row[key] = value[1:]

            for key, value in row.items():
                field = frappe.get_meta('Task').get_field(key)
                if value and field and field.fieldtype in ('Int', 'Float', 'Currency', 'Percent', 'Check'):
                    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value):
                        frappe.throw(f'Row {number}: {key} needs a plain number.')
                    try:
                        numeric = Decimal(value)
                    except InvalidOperation:
                        frappe.throw(f'Row {number}: {key} needs a finite number.')
                    if not numeric.is_finite() or (field.fieldtype == 'Int' and numeric != numeric.to_integral_value()) or (field.fieldtype == 'Check' and numeric not in (0, 1)):
                        frappe.throw(f'Row {number}: {key} has an invalid numeric value.')
            if not row.get('subject'):

                frappe.throw(f'Row {number} needs a subject.')
            if row.get('name'):
                doc = require_permission('Task', row['name'], 'write')
                if doc.project != project:
                    frappe.throw(f'Row {number} belongs to another project.')
            rows.append(row)
        if not rows:
            frappe.throw('The CSV contains no task rows.')
        names = [row['name'] for row in rows if row.get('name')]
        if len(names) != len(set(names)):
            frappe.throw('A task ID can only appear once per import.')
        return rows
    except csv.Error:
        frappe.throw('The CSV could not be read. Check its quoting and column count.')


@frappe.whitelist()
def preview_import(project, content):
    rows = _parse(project, content)
    return {'count': len(rows), 'create': sum(not row.get('name') for row in rows),
            'update': sum(bool(row.get('name')) for row in rows), 'rows': rows[:10],
            'columns': list(_columns(project, 'write'))}


@frappe.whitelist(methods=['POST'])
def import_tasks(project, content):
    rows = _parse(project, content)
    fingerprint = hashlib.sha256((project + '\n' + json.dumps(rows, sort_keys=True)).encode()).hexdigest()
    # Serialize all imports into one project, including concurrent retries.
    frappe.db.sql('select name from `tabProject` where name=%s for update', project)
    existing = frappe.db.get_value('Pulse Import Batch', fingerprint, 'result', for_update=True)
    if existing:
        result = json.loads(existing) if isinstance(existing, str) else existing
        for name in result['created'] + result['updated']:
            if not frappe.has_permission('Task', 'write', doc=name):
                frappe.throw('This import result contains tasks you cannot access.', frappe.PermissionError)
        return {**result, 'replayed': True}
    from pulse.services.atomic import atomic_scope
    with atomic_scope('pulse_import'):
        result = {'created': [], 'updated': [], 'replayed': False}
        for row in rows:
            values = {key: value for key, value in row.items() if key != 'name'}
            for field in ('exp_start_date', 'exp_end_date', 'type'):
                if field in values and not values[field]:
                    values[field] = None
            if row.get('name'):
                doc = frappe.get_doc('Task', row['name'], for_update=True)
                doc.check_permission('write')
                if doc.project != project:
                    frappe.throw('A task moved to another project. Preview the import again.')
                doc.update(values)
                doc.save()
                result['updated'].append(doc.name)
            else:
                doc = frappe.get_doc({'doctype': 'Task', 'project': project, **values}).insert()
                result['created'].append(doc.name)
        frappe.get_doc({'doctype': 'Pulse Import Batch', 'project': project,
                        'fingerprint': fingerprint, 'result': json.dumps(result)}).insert(ignore_permissions=True)
    return result


def _cell(value):
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    text = '' if value is None else str(value)
    # Spreadsheet programs execute formula-like cell contents when opening CSV.
    return "'" + text if text.startswith("'") or text.lstrip().startswith(('=', '+', '-', '@')) else text


@frappe.whitelist()
def export_tasks(project):
    require_permission('Project', project)
    columns = _columns(project, 'read')
    rows = frappe.get_list('Task', filters={'project': project}, fields=list(columns),
                           order_by='creation asc', limit_page_length=0)
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows([_cell(row.get(key)) for key in columns] for row in rows)
    return {'filename': 'pulse-tasks.csv', 'content': output.getvalue(), 'count': len(rows)}


@frappe.whitelist()
def csv_template(project=None):
    if project:
        require_permission('Project', project, 'write')
    columns = _columns(project, 'write') if project else COLUMNS
    return {'filename': 'pulse-task-template.csv', 'content': ','.join(columns) + '\n'}
