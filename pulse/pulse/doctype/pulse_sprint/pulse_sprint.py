import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PulseSprint(Document):
	def validate(self):
		self.validate_dates()
		self.sync_is_active()
		self.enforce_single_active_sprint()

	def validate_dates(self):
		if self.start_date and self.end_date and self.start_date > self.end_date:
			frappe.throw(_("Start Date cannot be after End Date."))

	def sync_is_active(self):
		self.is_active = 1 if self.status == "Active" else 0

	def enforce_single_active_sprint(self):
		"""A project may have at most one Active sprint at a time."""
		if self.status != "Active":
			return
		existing = frappe.get_all(
			"Pulse Sprint",
			filters={
				"project": self.project,
				"status": "Active",
				"name": ["!=", self.name or ""],
			},
			pluck="name",
		)
		if existing:
			frappe.throw(
				_("Project {0} already has an active sprint ({1}). Close it first.").format(
					self.project, existing[0]
				)
			)

	def on_update(self):
		self.recalculate_tasks()

	def recalculate_tasks(self):
		"""Roll task counts up from the Tasks linked to this sprint.

		Progress is measured in task count (Pulse does not use story points).
		Actual effort lives on the timesheets.
		"""
		rows = frappe.get_all(
			"Task",
			filters={"pulse_sprint": self.name},
			fields=["status"],
		)
		planned = len(rows)
		completed = sum(1 for r in rows if r.status == "Completed")
		# Use db_set to avoid recursive save loops.
		self.db_set("planned_tasks", planned, update_modified=False)
		self.db_set("completed_tasks", completed, update_modified=False)
		if self.status == "Completed":
			self.db_set("velocity", completed, update_modified=False)
