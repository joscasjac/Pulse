import frappe
from frappe import _

from pulse.services.hierarchy_service import can_assign, hierarchy_enabled


def enforce_hierarchy(doc, method=None):
    if getattr(doc, "doctype", None) != "ToDo":
        return
    if doc.get("reference_type") == "Task" and doc.get("reference_name"):
        from pulse.hooks.permissions import require_permission
        require_permission("Task", doc.reference_name, "write")
    assignee = doc.get("allocated_to")
    if not assignee:
        return
    if not hierarchy_enabled():
        return
    assigner = frappe.session.user
    if assigner in ("Administrator",):
        return
    if not can_assign(assigner, assignee):
        frappe.throw(
            _(
                "You can only assign work to people at or below your role level. "
                "{0} is ranked above you."
            ).format(frappe.bold(assignee)),
            title=_("Assignment not allowed"),
        )


def validate_assignment(assigner, assignee, doc=None):
    if not hierarchy_enabled():
        return
    if assigner in ("Administrator",) or "Pulse Admin" in frappe.get_roles(assigner):
        return
    if assigner == assignee:
        return
    if not can_assign(assigner, assignee):
        frappe.throw(
            _(
                "You cannot assign work to {0}: their role rank ({1}) is higher than yours ({2}). "
                "Assignment is allowed only down or across the hierarchy."
            ).format(
                assignee,
                _get_rank(assignee),
                _get_rank(assigner),
            ),
            title=_("Assignment Not Allowed"),
        )


def _get_rank(user):
    from pulse.services.hierarchy_service import get_user_max_rank

    return get_user_max_rank(user)
