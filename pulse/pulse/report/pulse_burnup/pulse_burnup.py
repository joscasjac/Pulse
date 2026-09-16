"""Historical sprint chart based only on recorded snapshots."""
from pulse.api.reports import sprint_history_report


def execute(filters=None):
    return sprint_history_report(filters)
