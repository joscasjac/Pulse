"""Average submitted time-entry duration, from permitted native records only."""
import frappe
from frappe import _
from pulse.api.time import _entries


def execute(filters=None):
    columns = [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
        {"label": _("Average Hours per Entry"), "fieldname": "average_hours", "fieldtype": "Float", "width": 180},
        {"label": _("Submitted Entries"), "fieldname": "entries", "fieldtype": "Int", "width": 150},
    ]
    visible = set(frappe.get_list("Project", pluck="name", limit_page_length=0))
    totals = {}
    for entry in _entries():
        if entry["docstatus"] != 1 or entry["project"] not in visible:
            continue
        row = totals.setdefault(entry["project"], {"project": entry["project"], "hours": 0, "entries": 0})
        row["hours"] += entry["hours"]
        row["entries"] += 1
    return columns, [{"project": row["project"], "average_hours": row["hours"] / row["entries"],
                      "entries": row["entries"]} for row in sorted(totals.values(), key=lambda row: row["project"])]
