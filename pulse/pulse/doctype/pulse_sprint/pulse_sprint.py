import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime


def _frozen_value(doc, field):
	value = doc.get(field) if doc else None
	if not value:
		return None
	if field in ("history_started_at", "closed_at"):
		return get_datetime(value)
	if field in ("start_date", "end_date"):
		return getdate(value)
	return value


class PulseSprint(Document):
	def validate(self):
		self.validate_dates()
		old = self.get_doc_before_save()
		if not frappe.flags.get("pulse_migration"):
			if _frozen_value(self, "history_started_at") != _frozen_value(old, "history_started_at"):
				frappe.throw("The recorded history start cannot be changed.")
			if not self.flags.get("pulse_closing") and any(_frozen_value(self, field) != _frozen_value(old, field) for field in ("closed_at", "closure_summary")):
				frappe.throw("Close the sprint through Pulse planning to record its outcome.")
		if old and old.status == "Active" and self.status == "Planned":
			frappe.throw("An active sprint must be closed before planning another cycle.")
		if self.status == "Active" and (not self.start_date or not self.end_date):
			frappe.throw("Set the sprint start and end dates before starting.")
		if old and old.project != self.project and (old.status != "Planned" or frappe.db.exists("Task", {"pulse_sprint": self.name})):
			frappe.throw("A sprint with tasks or recorded history cannot change projects.")
		if old and old.status == "Completed" and self.status != "Completed":
			frappe.throw("Completed sprints cannot be reopened.")
		if self.status == "Completed" and (not old or old.status != "Completed") and not self.flags.get("pulse_closing"):
			frappe.throw("Close the sprint through Pulse planning to choose how unfinished work is handled.")
		if old and old.status == "Completed" and any(_frozen_value(self, field) != _frozen_value(old, field) for field in ("closure_summary", "closed_at", "history_started_at", "progress_measure", "project", "start_date", "end_date", "goal")):
			frappe.throw("Completed sprint history and metrics are frozen.")
		self.sync_is_active()
		self.enforce_single_active_sprint()

	def validate_dates(self):
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
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
		if self.status == "Active" and not self.get("history_started_at"):
			from pulse.api.sprint_history import baseline
			from frappe.utils import now_datetime
			self.db_set("history_started_at", now_datetime(), update_modified=False)
			baseline(self)
		self.recalculate_tasks()

	def recalculate_tasks(self):
		"""Roll task counts up from the Tasks linked to this sprint.

		These legacy counters remain task counts; planning endpoints also
		measure estimated hours and points. Closed counters use frozen outcomes.
		"""
		if self.status == "Completed" and self.get("closure_summary"):
			summary = frappe.parse_json(self.closure_summary)
			self.db_set("planned_tasks", summary["tasks"], update_modified=False)
			self.db_set("completed_tasks", summary["completed_tasks"], update_modified=False)
			self.db_set("velocity", summary["completed_tasks"], update_modified=False)
			return
		rows = frappe.get_all(
			"Task",
			filters={"pulse_sprint": self.name, "pulse_archived": 0},
			fields=["status"],
		)
		planned = len(rows)
		completed = sum(1 for r in rows if r.status == "Completed")
		# Use db_set to avoid recursive save loops.
		self.db_set("planned_tasks", planned, update_modified=False)
		self.db_set("completed_tasks", completed, update_modified=False)
		if self.status == "Completed":
			self.db_set("velocity", completed, update_modified=False)
