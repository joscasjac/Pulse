"""Shared reads of dependency edges between already-authorized task endpoints."""
import frappe


def visible_dependencies(visible, active_only=False):
    """Merge native and Pulse edges: source depends on target in both contracts.

    Native children are read only here; no mirrored dependency writes or hooks.
    Child queries are bounded to already permission-filtered endpoints, and the
    explicit source metadata prevents a native edge being mistaken for a Pulse ID.
    """
    if not visible:
        return []
    names = sorted(visible)
    edges = {}
    for offset in range(0, len(names), 200):
        parents = names[offset:offset + 200]
        scope = {'source_task': ['in', parents]}
        if active_only:
            scope['status'] = 'Active'
        for row in frappe.get_list('Pulse Dependency', filters=scope,
                                   fields=['name', 'source_task', 'target_task'], limit_page_length=0):
            if row.target_task not in visible:
                continue
            key = (row.source_task, row.target_task)
            if key not in edges:
                edges[key] = dict(name=row.name, source_task=row.source_task, target_task=row.target_task,
                                  sources=['pulse'], pulse_name=row.name)
        # Child records do not carry independent permissions. Both endpoints
        # must be in visible, including the native parent and prerequisite.
        for row in frappe.get_all('Task Depends On', filters={'parent': ['in', parents],
                                  'parenttype': 'Task', 'parentfield': 'depends_on'},
                                  fields=['name', 'parent', 'task'], limit_page_length=0):
            if row.task not in visible:
                continue
            key = (row.parent, row.task)
            if key in edges:
                if 'erpnext' not in edges[key]['sources']:
                    edges[key]['sources'].append('erpnext')
                edges[key]['native_name'] = row.name
            else:
                edges[key] = dict(name='native:' + row.name, source_task=row.parent, target_task=row.task,
                                  sources=['erpnext'], native_name=row.name)
    return list(edges.values())

