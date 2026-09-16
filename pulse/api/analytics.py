"""Permission-scoped task analytics."""
import frappe
from frappe.utils import today
from pulse.services.analytics import summarize


@frappe.whitelist()
def get_analytics(project=None):
    if project:
        from pulse.hooks.permissions import require_permission
        require_permission("Project", project)
    # Load visible tasks across projects so a visible cross-project dependency
    # can block a selected project's task without broadening the metric scope.
    visible = frappe.get_list(
        "Task", filters={"pulse_archived": 0}, fields=["name", "status", "workflow_state", "priority", "exp_end_date",
                        "type", "project", "_assign", "pulse_sprint"], limit_page_length=0)
    selected = [t for t in visible if not project or t.get("project") == project]
    names = {t["name"] for t in visible}
    from pulse.services.dependencies import visible_dependencies
    dependencies = visible_dependencies(names, active_only=True)
    # Carry only the dependency blocker outcome into the selected task set.
    visible_map = {t["name"]: t for t in visible}
    blocked = {d["source_task"] for d in dependencies
               if visible_map[d["target_task"]].get("status") not in {"Completed", "Cancelled"}}
    from pulse.api.task_config import statuses_for
    categories = {p: {state["label"]: state["category"] for state in statuses_for(p)}
                  for p in {t.get("project") for t in selected}}
    selected = [dict(t, is_blocked=(t["name"] in blocked or
                  categories[t.get("project")].get(t.get("workflow_state")) == "Blocked"))
                for t in selected]
    sprints = frappe.get_list(
        "Pulse Sprint", filters={"project": project} if project else {},
        fields=["name", "sprint_name", "status"], order_by="start_date desc", limit_page_length=6)
    return summarize(selected, [], sprints, today())
