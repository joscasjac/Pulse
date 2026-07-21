"""Sprint lifecycle automation."""

import frappe
from frappe.utils import today


def auto_close_sprints():
	"""Complete any Active sprint whose end_date has passed.

	Saving through the document API runs validate/on_update, which captures
	velocity (completed task count at close).
	"""
	due = frappe.get_all(
		"Pulse Sprint",
		filters={"status": "Active", "end_date": ["<", today()]},
		pluck="name",
	)
	for name in due:
		try:
			sprint = frappe.get_doc("Pulse Sprint", name)
			sprint.status = "Completed"
			sprint.save(ignore_permissions=True)
		except Exception:
			frappe.log_error(title="Pulse: auto-close sprint failed", message=frappe.get_traceback())
