from frappe.model.document import Document


class PulseTaskStatusLog(Document):
	"""Append-only. Rows are created by the Task on_update doc-event.

	Intentionally has no business logic: it is an immutable audit/metrics
	record read by the Pulse reports (burndown, CFD, cycle time, lead time).
	"""

	pass
