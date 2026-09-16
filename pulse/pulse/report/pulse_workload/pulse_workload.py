"""Permission-scoped estimated work compared with allocation and leave capacity."""
from frappe.utils import today, add_days
from pulse.api.business import workload


def execute(filters=None):
    filters = filters or {}
    start = filters.get('start_date') or today()
    end = filters.get('end_date') or add_days(start, 13)
    result = workload(start, end, filters.get('project'))
    columns = [
        {'label': 'Team member', 'fieldname': 'user', 'fieldtype': 'Data', 'width': 220},
        {'label': 'Estimated hours', 'fieldname': 'estimated_hours', 'fieldtype': 'Float', 'width': 150},
        {'label': 'Available hours', 'fieldname': 'available_hours', 'fieldtype': 'Float', 'width': 150},
        {'label': 'Over capacity (hours)', 'fieldname': 'over_hours', 'fieldtype': 'Float', 'width': 170},
    ]
    return columns, result['rows']
