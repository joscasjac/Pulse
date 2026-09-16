"""Atomic task edits and activity on the canonical ERPNext Task."""
import json

import frappe
from pulse.hooks.permissions import require_permission
from pulse.api.task_config import statuses_for

EDITABLE = {"subject", "description", "priority", "type", "project", "workflow_state",
            "exp_start_date", "exp_end_date", "expected_time", "pulse_story_points",
            "pulse_sprint", "pulse_epic", "pulse_release", "pulse_archived", "pulse_labels"}


def refresh_dependency_projects(doc, method=None):
    """Keep derived dependency project links aligned with native Task moves."""
    before = doc.get_doc_before_save()
    if not before or before.project == doc.project:
        return
    if not frappe.db.table_exists("Pulse Dependency"):
        return
    # These are derived references, not edits to dependency semantics. Update
    # both directions, including records hidden from the mover, atomically with
    # the already-authorized Task save. Do not change dependency activity dates.
    for endpoint in ("source", "target"):
        frappe.db.set_value("Pulse Dependency", {f"{endpoint}_task": doc.name},
                            f"{endpoint}_project", doc.project, update_modified=False)


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _prepare_fields(fields):
    fields = dict(_json(fields) or {})
    if "task_type" in fields:
        fields["type"] = fields.pop("task_type")
    if set(fields) - EDITABLE:
        frappe.throw("Unsupported task fields: " + ", ".join(sorted(set(fields) - EDITABLE)))
    if "pulse_labels" in fields:
        labels = _json(fields["pulse_labels"])
        if not isinstance(labels, list):
            frappe.throw("Labels must be a list.")
        fields["pulse_labels"] = [{"label": r.get("label") if isinstance(r, dict) else r} for r in labels]
    if "pulse_archived" in fields:
        if str(fields["pulse_archived"]) not in ("0", "1", "False", "True"):
            frappe.throw("Archived must be a boolean.")
        fields["pulse_archived"] = int(str(fields["pulse_archived"]) in ("1", "True"))
    return fields


def _hierarchy_order_for_move(docs, destination):
    """Validate the final parent/child graph before saving any selected task."""
    selected = {doc.name: doc for doc in docs}
    destination = destination or None
    for doc in docs:
        parent = doc.get("parent_task")
        if parent and parent not in selected:
            parent_project = frappe.db.get_value("Task", parent, "project") or None
            if parent_project != destination:
                frappe.throw("Move the parent and all its subtasks together to keep them in the same project.")
    # Internal relationship check includes children the caller cannot read. It never
    # exposes their identities or silently edits tasks outside the selected set.
    children = frappe.get_all("Task", filters={"parent_task": ["in", list(selected)]},
                              fields=["name", "project"], limit_page_length=0)
    if any(row.name not in selected and (row.project or None) != destination for row in children):
        frappe.throw("Move the parent and all its subtasks together to keep them in the same project.")
    ordered, visiting, visited = [], set(), set()

    def visit(doc):
        if doc.name in visiting:
            frappe.throw("Task hierarchy contains a cycle. Correct it before moving tasks.")
        if doc.name in visited:
            return
        visiting.add(doc.name)
        parent = selected.get(doc.get("parent_task"))
        if parent:
            visit(parent)
        visiting.remove(doc.name)
        visited.add(doc.name)
        ordered.append(doc)

    for doc in docs:
        visit(doc)
    return ordered


@frappe.whitelist()
def bulk_update(tasks, fields=None, assign=None, unassign=None):
    """All selected edits succeed together; any permission/validation error rolls back."""
    tasks = _json(tasks)
    if not isinstance(tasks, list) or not tasks or len(tasks) > 200 or any(not isinstance(t, str) for t in tasks):
        frappe.throw("Select between 1 and 200 task names.")
    names = list(dict.fromkeys(tasks))
    changes = _prepare_fields(fields)
    assign, unassign = _json(assign) or [], _json(unassign) or []
    if not isinstance(assign, list) or not isinstance(unassign, list):
        frappe.throw("Assignments must be lists of users.")
    if any(not isinstance(u, str) for u in assign + unassign):
        frappe.throw("Assignments must contain user names.")
    docs = [require_permission("Task", name, "write") for name in names]
    if changes.get("project"):
        require_permission("Project", changes["project"])
    if "project" in changes:
        docs = _hierarchy_order_for_move(docs, changes["project"])
    from pulse.hooks.events.assignment import validate_assignment
    for user in assign:
        validate_assignment(frappe.session.user, user)
    # Frappe request transactions provide final commit; savepoint protects direct calls too.
    savepoint = "pulse_bulk_" + frappe.generate_hash(length=10)
    frappe.db.savepoint(savepoint)
    previous_moves = frappe.flags.get("pulse_pending_task_projects")
    if "project" in changes:
        frappe.flags.pulse_pending_task_projects = {doc.name: changes["project"] or None for doc in docs}
    try:
        from frappe.desk.form.assign_to import add, remove
        for doc in docs:
            previous_project = doc.project
            old_statuses = {r["label"]: r for r in statuses_for(previous_project)}
            old_category = old_statuses.get(doc.get("workflow_state"), {}).get("category")
            doc.update(changes)
            if doc.project != previous_project:
                if "pulse_sprint" not in changes:
                    doc.pulse_sprint = None
                if "pulse_labels" not in changes:
                    doc.set("pulse_labels", [])
                if "workflow_state" not in changes:
                    candidates = [r for r in statuses_for(doc.project) if r["category"] == old_category]
                    if not candidates:
                        frappe.throw("Choose a destination status when moving between these projects.")
                    doc.workflow_state = candidates[0]["label"]
            doc.save()
            for user in unassign:
                remove("Task", doc.name, user)
            for user in assign:
                add({"assign_to": [user], "doctype": "Task", "name": doc.name})
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
    finally:
        frappe.flags.pulse_pending_task_projects = previous_moves
    frappe.publish_realtime("pulse:board", {}, after_commit=True)
    return {"updated": names, "count": len(names)}


@frappe.whitelist(methods=["POST"])
def move_task(task, state, before=None, after=None):
    """Insert before the next row and/or after the previous row in a status group.

    Serialize ordering changes per project. Integer ranks are normalized internally;
    neighboring records retain their modification dates and field history.
    """
    if not isinstance(task, str) or not isinstance(state, str) or not state:
        frappe.throw("Choose a task and destination status.")
    if any(anchor is not None and not isinstance(anchor, str) for anchor in (before, after)):
        frappe.throw("Task neighbors must be task names.")
    before, after = before or None, after or None
    if task in (before, after) or (before and before == after):
        frappe.throw("Choose different neighboring tasks.")
    doc = require_permission("Task", task, "write")
    if not doc.project or doc.get("pulse_archived"):
        frappe.throw("Only active project tasks can be reordered.")
    project = doc.project
    savepoint = "pulse_move_" + frappe.generate_hash(length=10)
    frappe.db.savepoint(savepoint)
    try:
        frappe.db.sql("select name from `tabProject` where name=%s for update", project)
        # Refresh after acquiring the lock so a concurrent move cannot use stale state.
        doc = require_permission("Task", task, "write")
        if doc.project != project or doc.get("pulse_archived"):
            frappe.throw("The task changed. Refresh and try again.")
        if state not in {row["label"] for row in statuses_for(project)}:
            frappe.throw("Choose a status configured for this project.")
        for anchor in (before, after):
            if not anchor:
                continue
            neighbor = require_permission("Task", anchor)
            if neighbor.project != project or neighbor.workflow_state != state or neighbor.get("pulse_archived"):
                frappe.throw("The neighboring task changed. Refresh and try again.")
        # Internal ordering metadata includes hidden rows, but none are returned.
        rows = frappe.get_all("Task", filters={"project": project, "workflow_state": state,
                                               "pulse_archived": 0, "name": ["!=", task]},
                              fields=["name", "pulse_rank"],
                              order_by="pulse_rank asc, modified desc, name asc", limit_page_length=5001)
        if len(rows) > 5000:
            frappe.throw("This status has too many tasks to reorder at once.")
        names = [row.name for row in rows]
        if any(anchor and anchor not in names for anchor in (before, after)):
            frappe.throw("The neighboring task changed. Refresh and try again.")
        if before and after and names.index(after) >= names.index(before):
            frappe.throw("The task order changed. Refresh and try again.")
        index = names.index(before) if before else names.index(after) + 1 if after else len(names)
        names.insert(index, task)
        doc.workflow_state = state
        doc.pulse_rank = (index + 1) * 1024
        doc.save()
        ranks = {row.name: row.pulse_rank for row in rows}
        for position, name in enumerate(names, 1):
            rank = position * 1024
            if name != task and ranks.get(name) != rank:
                frappe.db.set_value("Task", name, "pulse_rank", rank, update_modified=False)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
    frappe.publish_realtime("pulse:board", {}, after_commit=True)
    return {"name": doc.name, "workflow_state": doc.workflow_state, "pulse_rank": doc.pulse_rank}


@frappe.whitelist()
def activity(task, limit=100):
    require_permission("Task", task)
    limit = max(1, min(int(limit), 500))
    # Version is internal; parent Task read permission is the authorization boundary.
    rows = frappe.get_all("Version", filters={"ref_doctype": "Task", "docname": task},
                          fields=["name", "owner", "creation", "data"],
                          order_by="creation desc", limit_page_length=limit)
    result = []
    for row in rows:
        data = frappe.parse_json(row.data or "{}") or {}
        result.append({"name": row.name, "user": row.owner, "at": row.creation,
                       "changed": data.get("changed", []), "added": data.get("added", []),
                       "removed": data.get("removed", []), "row_changed": data.get("row_changed", [])})
    refs = [task]
    key = frappe.db.get_value("Task", task, "issue_key")
    if key:
        refs.append(key)
    for row in frappe.get_list("Pulse Activity Log", filters={"reference_doctype": "Task", "reference_name": ["in", refs], "activity_type": "Assignment Changed"},
                               fields=["name", "user", "creation", "description"], order_by="creation desc", limit_page_length=limit):
        result.append({"name": row.name, "user": row.user, "at": row.creation, "description": row.description,
                       "changed": [], "added": [], "removed": [], "row_changed": []})
    return sorted(result, key=lambda r: str(r["at"]), reverse=True)[:limit]


def record_assignment(doc, method=None):
    """Track assignments from Desk, Pulse and REST through native ToDo events."""
    if doc.get("reference_type") != "Task" or not doc.get("reference_name"):
        return
    before = doc.get_doc_before_save()
    if method == "on_update" and before is None:
        return  # The initial insert is recorded by after_insert.
    from pulse.api.audit import log
    project = frappe.db.get_value("Task", doc.reference_name, "project")
    old_user = before.get("allocated_to") if before and before.get("status") == "Open" else None
    new_user = doc.get("allocated_to") if method != "on_trash" and doc.get("status") == "Open" else None
    if method == "on_trash":
        old_user = doc.get("allocated_to") if doc.get("status") == "Open" else None
    if old_user == new_user:
        return
    if old_user:
        log("Assignment Changed", "Task", doc.reference_name, project, f"Unassigned {old_user}")
    if new_user:
        log("Assignment Changed", "Task", doc.reference_name, project, f"Assigned {new_user}")
