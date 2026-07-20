"""Pulse Recurring Task — a template that auto-generates real Tasks on a schedule.

The scheduler (pulse.scheduled.recurring.generate_due) creates a Task in the
"To Do" column each time `next_run` is reached, then advances `next_run` by the
configured interval, so routine work never rots in the backlog.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, getdate, today


class PulseRecurringTask(Document):
    def validate(self):
        if not self.start_date:
            self.start_date = today()
        if not self.interval_count or int(self.interval_count) < 1:
            self.interval_count = 1
        if not self.next_run:
            self.next_run = self.start_date

    def advance_next_run(self, from_date=None):
        """Move next_run forward by one interval from `from_date` (or current next_run)."""
        base = getdate(from_date or self.next_run or today())
        n = int(self.interval_count or 1)
        unit = self.interval_unit or "Week"
        if unit == "Day":
            self.next_run = add_days(base, n)
        elif unit == "Month":
            self.next_run = add_months(base, n)
        else:  # Week
            self.next_run = add_days(base, 7 * n)
        return self.next_run
