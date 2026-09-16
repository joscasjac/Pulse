import frappe
from frappe.model.document import Document


class PulseSettings(Document):
	def validate(self):
		from pulse.scheduled.reminders import parse_reminder_days
		try:
			parse_reminder_days(self.get("reminder_days_before"))
		except ValueError as exc:
			frappe.throw(str(exc))

	def get_role_rank_map(self):
		"""Return {role: rank} from the configured Role Ranks table."""
		return {r.role: int(r.rank or 0) for r in (self.role_ranks or [])}

	def on_update(self):
		frappe.cache().delete_value("pulse_role_rank_map")


@frappe.whitelist()
def get_role_rank_map():
	"""Cached role -> rank map used by the assignment-hierarchy check."""
	def _build():
		settings = frappe.get_single("Pulse Settings")
		return settings.get_role_rank_map()

	return frappe.cache().get_value("pulse_role_rank_map", generator=_build)


def clear_role_rank_cache(doc=None, method=None):
	frappe.cache().delete_value("pulse_role_rank_map")
