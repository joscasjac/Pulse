"""Frozen closure outcomes or current permission-filtered sprint progress."""
from pulse.api.planning import sprint_progress


def execute(filters=None):
    filters = filters or {}
    if not filters.get("sprint"):
        return [], []
    summary = sprint_progress(filters["sprint"])
    columns = [{"fieldname": "metric", "label": "Metric", "fieldtype": "Data", "width": 220},
               {"fieldname": "value", "label": "Value", "fieldtype": "Data", "width": 400}]
    return columns, [{"metric": key.replace("_", " ").title(),
                      "value": ", ".join(map(str, value)) if isinstance(value, list) else value}
                     for key, value in summary.items()]
