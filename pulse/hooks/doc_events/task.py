import re

import frappe
from frappe.utils import now_datetime


def before_insert(doc, method=None):
    assign_issue_key(doc)


def on_update(doc, method=None):
    _log_status_change(doc)
    _rollup_sprint_points(doc)


# ---------------------------------------------------------------------------
# Human-readable issue keys (e.g. OPS-9)
# ---------------------------------------------------------------------------

def assign_issue_key(doc):
    if doc.get("issue_key") or not doc.get("project"):
        return
    key = ensure_project_key(doc.project)
    # atomic per-project sequence
    frappe.db.sql(
        "UPDATE `tabPulse Project` SET task_counter = COALESCE(task_counter, 0) + 1 WHERE name = %s",
        (doc.project,),
    )
    seq = frappe.db.get_value("Pulse Project", doc.project, "task_counter")
    doc.seq = seq
    doc.issue_key = f"{key}-{seq}"


def ensure_project_key(project):
    key = frappe.db.get_value("Pulse Project", project, "pulse_project_key")
    if key:
        return key
    name = frappe.db.get_value("Pulse Project", project, "project_name") or project
    key = _make_key(name)
    # guarantee uniqueness across projects
    base, n = key, 1
    taken = set(
        frappe.get_all("Pulse Project", filters={"name": ["!=", project]},
                       pluck="pulse_project_key")
    )
    while key in taken:
        n += 1
        key = f"{base}{n}"
    frappe.db.set_value("Pulse Project", project, "pulse_project_key", key)
    return key


def _make_key(name):
    words = re.findall(r"[A-Za-z0-9]+", (name or "").upper())
    if not words:
        return "PRJ"
    if len(words) == 1:
        return words[0][:4]
    return "".join(w[0] for w in words)[:5]


def _log_status_change(doc):
    to_state = doc.get("workflow_state") or doc.status
    if not to_state:
        return
    
    status_map = {
        "Open": "To Do",
        "Working": "In Progress",
        "Pending Review": "In Review",
        "Completed": "Done",
        "Cancelled": "Cancelled"
    }
    if to_state in status_map:
        to_state = status_map[to_state]
        
    before = doc.get_doc_before_save()
    from_state = (before.get("workflow_state") or before.status) if before is not None else None
    if from_state in status_map:
        from_state = status_map[from_state]
        
    if before is not None and from_state == to_state:
        return
    log = frappe.new_doc("Pulse Task Status Log")
    log.task = doc.name
    log.project = doc.project
    log.sprint = doc.get("pulse_sprint")
    log.from_state = from_state
    log.to_state = to_state
    log.changed_by = frappe.session.user
    log.changed_on = now_datetime()
    log.points_at_change = doc.get("pulse_story_points") or 0
    log.insert(ignore_permissions=True)


def _rollup_sprint_points(doc):
    sprint = doc.get("pulse_sprint")
    if not sprint or not frappe.db.exists("Pulse Sprint", sprint):
        return
    before = doc.get_doc_before_save()
    old_sprint = before.get("pulse_sprint") if before else None
    old_points = before.get("pulse_story_points") if before else None
    new_points = doc.get("pulse_story_points")
    if sprint == old_sprint and old_points == new_points:
        return
    try:
        frappe.get_doc("Pulse Sprint", sprint).recalculate_points()
    except Exception:
        frappe.log_error(
            title="Pulse: sprint point rollup failed",
            message=frappe.get_traceback(),
        )
    if (
        old_sprint
        and old_sprint != sprint
        and frappe.db.exists("Pulse Sprint", old_sprint)
    ):
        try:
            frappe.get_doc("Pulse Sprint", old_sprint).recalculate_points()
        except Exception:
            frappe.log_error(
                title="Pulse: sprint point rollup failed",
                message=frappe.get_traceback(),
            )
