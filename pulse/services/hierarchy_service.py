"""Role-hierarchy logic for Pulse assignment (assign-down-only).

Ranks are configured in Pulse Settings -> Role Ranks. A user's rank is the
MAX rank among the roles they hold. A user may assign work only to users whose
rank is at or below their own.
"""

import frappe


ADMIN_USERS = {"Administrator"}
BYPASS_ROLES = {"System Manager", "Pulse Admin"}


def get_role_rank_map():
	"""{role: rank}, cached; invalidated when Pulse Settings is saved."""
	def _build():
		if not frappe.db.exists("DocType", "Pulse Settings"):
			return {}
		settings = frappe.get_single("Pulse Settings")
		return {r.role: int(r.rank or 0) for r in (settings.role_ranks or [])}

	return frappe.cache().get_value("pulse_role_rank_map", generator=_build) or {}


def get_user_max_rank(user):
	"""Highest configured rank among the user's roles (0 if none)."""
	if not user or user in ADMIN_USERS:
		return float("inf")
	rank_map = get_role_rank_map()
	if not rank_map:
		return 0
	roles = set(frappe.get_roles(user))
	if roles & BYPASS_ROLES:
		return float("inf")
	ranks = [rank_map[r] for r in roles if r in rank_map]
	return max(ranks) if ranks else 0


def hierarchy_enabled():
	if not frappe.db.exists("DocType", "Pulse Settings"):
		return False
	return bool(frappe.db.get_single_value("Pulse Settings", "enable_hierarchical_assignment"))


def can_assign(assigner, assignee):
	"""True if `assigner` may assign work to `assignee`."""
	if assigner == assignee:
		return True
	return get_user_max_rank(assigner) >= get_user_max_rank(assignee)
