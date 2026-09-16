"""Project task vocabulary, validated on every native document write."""
import json
import math
import re

import frappe
from frappe.utils import getdate
from pulse.hooks.permissions import require_permission

CATEGORY_STATUS = {"Backlog": "Open", "To Do": "Open", "In Progress": "Working",
                   "In Review": "Pending Review", "Blocked": "Open", "Done": "Completed", "Cancelled": "Cancelled"}
DEFAULT_STATUSES = [
    {"label": "Backlog", "color": "#64748b", "category": "Backlog"},
    {"label": "To Do", "color": "#3b82f6", "category": "To Do"},
    {"label": "In Progress", "color": "#f59e0b", "category": "In Progress"},
    {"label": "In Review", "color": "#8b5cf6", "category": "In Review"},
    {"label": "Blocked", "color": "#ef4444", "category": "Blocked"},
    {"label": "Done", "color": "#22c55e", "category": "Done"},
    {"label": "Cancelled", "color": "#94a3b8", "category": "Cancelled"},
]


def statuses_for(project):
    # Internal validator helper, no data returned directly without a checked parent.
    doc = frappe.get_doc("Project", project) if isinstance(project, str) else project
    rows = doc.get("pulse_task_statuses") if doc else []
    return [{"label": r.label, "color": r.color, "category": r.category} for r in rows] if rows else [dict(r) for r in DEFAULT_STATUSES]


def _color(value):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value or ""):
        frappe.throw("Choose a six-digit hex color, for example #3b82f6.")


def validate_project_config(doc, method=None):
    rows = doc.get("pulse_task_statuses") or []
    names = set()
    for row in rows:
        row.label = (row.label or "").strip()
        if not row.label or row.label in names:
            frappe.throw("Task status names must be nonempty and unique within a project.")
        names.add(row.label)
        _color(row.color)
        if row.category not in CATEGORY_STATUS:
            frappe.throw("Unknown task status category.")
    types = [r.task_type for r in doc.get("pulse_task_types") or []]
    if len(types) != len(set(types)):
        frappe.throw("A task type can only be configured once per project.")
    if not doc.is_new():
        allowed = names or {r["label"] for r in DEFAULT_STATUSES}
        # Elevated enumeration only validates existence; never returns hidden tasks.
        used = frappe.get_all("Task", filters={"project": doc.name}, fields=["workflow_state", "type"], limit_page_length=0)
        if any(t.workflow_state and t.workflow_state not in allowed for t in used):
            frappe.throw("Move tasks out of removed statuses before changing the project configuration.")
        before = doc.get_doc_before_save()
        if before:
            old_categories = {r["label"]: r["category"] for r in statuses_for(before)}
            new_categories = {r["label"]: r["category"] for r in statuses_for(doc)}
            if any(old_categories.get(t.workflow_state) != new_categories.get(t.workflow_state) for t in used if t.workflow_state in old_categories):
                frappe.throw("Move tasks to another status before changing a status category.")
        if types and any(t.type and t.type not in types for t in used):
            frappe.throw("Change existing tasks to allowed types before removing a task type.")


def validate_label(doc, method=None):
    require_permission("Project", doc.project, "write")
    _color(doc.color)
    doc.label_name = (doc.label_name or "").strip()
    if not doc.label_name:
        frappe.throw("A label name is required.")
    duplicates = frappe.get_all("Pulse Label", filters={"project": doc.project, "label_name": doc.label_name, "name": ["!=", doc.name or ""]}, pluck="name", limit_page_length=1)
    if duplicates:
        frappe.throw("This project already has a label with that name.")
    before = doc.get_doc_before_save()
    if before and before.project != doc.project and frappe.db.exists("Pulse Task Label", {"label": doc.name}):
        frappe.throw("A label used by tasks cannot be moved to another project.")


def validate_task(doc, method=None):
    if not doc.get("project"):
        statuses = statuses_for(None)
        project = None
    else:
        project = frappe.get_doc("Project", doc.project)
        statuses = statuses_for(project)
    by_name = {r["label"]: r for r in statuses}
    before = doc.get_doc_before_save()
    state = doc.get("workflow_state")
    status_changed = before and before.get("status") != doc.status
    state_changed = before and before.get("workflow_state") != state
    if not state or (status_changed and not state_changed):
        native = "Working" if doc.status == "Overdue" else doc.status
        candidates = [r for r in statuses if CATEGORY_STATUS[r["category"]] == native]
        if not candidates:
            frappe.throw("The project needs a task status matching this ERPNext status.")
        preferred = "To Do" if native == "Open" else None
        state = next((r["label"] for r in candidates if r["category"] == preferred), candidates[0]["label"])
    if state not in by_name:
        frappe.throw("Choose a task status configured for this project.")
    doc.workflow_state = state
    # Preserve ERPNext's automatic Overdue status while retaining its board category.
    if not (doc.status == "Overdue" and not state_changed and by_name[state]["category"] == "In Progress"):
        doc.status = CATEGORY_STATUS[by_name[state]["category"]]
    types = [r.task_type for r in project.get("pulse_task_types") or []] if project else []
    if types and doc.get("type") and doc.type not in types:
        frappe.throw("Choose a task type configured for this project.")
    for field in ("expected_time", "pulse_story_points"):
        number = float(doc.get(field) or 0)
        if not math.isfinite(number) or number < 0:
            frappe.throw("Task estimates must be finite nonnegative numbers.")
    if doc.get("exp_start_date") and doc.get("exp_end_date") and getdate(doc.exp_start_date) > getdate(doc.exp_end_date):
        frappe.throw("Task start date must be on or before its due date.")
    labels = set()
    for row in doc.get("pulse_labels") or []:
        if row.label in labels:
            frappe.throw("A task cannot have duplicate labels.")
        labels.add(row.label)
        if frappe.db.get_value("Pulse Label", row.label, "project") != doc.get("project"):
            frappe.throw("Task labels must belong to the same project as the task.")
    if doc.get("parent_task") and frappe.db.get_value("Task", doc.parent_task, "project") != doc.get("project"):
        frappe.throw("A subtask must belong to the same project as its parent.")
    if before and (before.get("project") or None) != (doc.get("project") or None):
        destination = doc.get("project") or None
        children = frappe.get_all("Task", filters={"parent_task": doc.name},
                                  fields=["name", "project"], limit_page_length=0)
        pending = frappe.flags.get("pulse_pending_task_projects") or {}
        for child in children:
            if (child.project or None) == destination:
                continue
            # Only bulk_update installs this map after checking every selected
            # task's write permission and the complete final hierarchy. A generic
            # save cannot bypass the invariant or silently move hidden children.
            if doc.name in pending and child.name in pending and pending[doc.name] == destination and pending[child.name] == destination:
                continue
            frappe.throw("Move the parent and all its subtasks together to keep them in the same project.")
    if doc.get("pulse_sprint") and frappe.db.get_value("Pulse Sprint", doc.pulse_sprint, "project") != doc.get("project"):
        frappe.throw("The task and sprint must belong to the same project.")


@frappe.whitelist()
def get_config(project):
    doc = require_permission("Project", project)
    types = [r.task_type for r in doc.get("pulse_task_types") or []]
    if not types:
        types = frappe.get_list("Task Type", pluck="name", limit_page_length=0)
    return {"statuses": statuses_for(doc), "task_types": types,
            "labels": frappe.get_list("Pulse Label", filters={"project": project}, fields=["name", "label_name", "color"], order_by="label_name asc", limit_page_length=0)}


@frappe.whitelist()
def save_config(project, statuses, task_types=None):
    doc = require_permission("Project", project, "write")
    statuses = json.loads(statuses) if isinstance(statuses, str) else statuses
    task_types = json.loads(task_types) if isinstance(task_types, str) else task_types
    if not isinstance(statuses, list) or not statuses:
        frappe.throw("Configure at least one task status.")
    doc.set("pulse_task_statuses", [{k: row.get(k) for k in ("label", "color", "category")} for row in statuses])
    if task_types is not None:
        doc.set("pulse_task_types", [{"task_type": name} for name in task_types])
    doc.save()
    return get_config(project)


@frappe.whitelist()
def save_label(project, label_name, color, name=None):
    require_permission("Project", project, "write")
    doc = require_permission("Pulse Label", name, "write") if name else frappe.new_doc("Pulse Label")
    doc.update({"project": project, "label_name": label_name, "color": color})
    doc.save()
    return {"name": doc.name, "label_name": doc.label_name, "color": doc.color}


def initialize_project_statuses():
    """Preserve legacy board names when enabling project-specific status validation."""
    native_categories = {"Open": "To Do", "Working": "In Progress", "Overdue": "In Progress",
                         "Pending Review": "In Review", "Completed": "Done", "Cancelled": "Cancelled"}
    for name in frappe.get_all("Project", pluck="name", limit_page_length=0):
        doc = frappe.get_doc("Project", name)
        if doc.get("pulse_task_statuses"):
            continue
        statuses = [dict(row) for row in DEFAULT_STATUSES]
        known = {r["label"] for r in statuses}
        for task in frappe.get_all("Task", filters={"project": name}, fields=["workflow_state", "status"], order_by="creation asc", limit_page_length=0):
            state = task.workflow_state
            if state and state not in known:
                statuses.append({"label": state, "color": "#64748b", "category": native_categories.get(task.status, "To Do")})
                known.add(state)
        doc.set("pulse_task_statuses", statuses)
        doc.save(ignore_permissions=True)
