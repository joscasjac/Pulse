"""Epics and releases (canonical namespace: pulse.api.planning.*).

An epic is simply a Task of type "Epic"; other tasks point at it via
`pulse_epic`. A release is the free-text `pulse_release` tag on a task.
Epics and releases roll up task counts; sprint progress also supports hours and points.
"""

import frappe

TASK_FIELDS = ["name", "issue_key", "subject", "status", "workflow_state",
               "priority", "project", "pulse_release", "pulse_epic"]


def _progress(rows):
    total = len(rows)
    done = sum(1 for r in rows if r.get("status") == "Completed")
    return {"total": total, "done": done,
            "pct": round(100 * done / total) if total else 0}


@frappe.whitelist()
def list_epics(project=None):
    """Epics (tasks of type Epic) with their child-task progress."""
    filters = {"type": "Epic"}
    if project:
        filters["project"] = project
    epics = frappe.get_list("Task", filters=filters,
                           fields=["name", "issue_key", "subject", "status",
                                   "workflow_state", "project"],
                           order_by="creation desc", limit_page_length=0)
    for e in epics:
        children = frappe.get_list("Task", filters={"pulse_epic": e["name"]},
                                  fields=["status"])
        e.update(_progress(children))
    return epics


@frappe.whitelist()
def epic_tasks(epic):
    return frappe.get_list("Task", filters={"pulse_epic": epic}, fields=TASK_FIELDS,
                          order_by="workflow_state asc, modified desc",
                          limit_page_length=0)


@frappe.whitelist()
def epic_options(project=None):
    """Epics available to link a task to (for the task drawer picker)."""
    filters = {"type": "Epic"}
    if project:
        filters["project"] = project
    return frappe.get_list("Task", filters=filters,
                          fields=["name", "issue_key", "subject"],
                          order_by="creation desc", limit_page_length=0)


@frappe.whitelist()
def list_releases(project=None):
    """Distinct release tags with task-count progress."""
    filters = {"pulse_release": ["!=", ""]}
    if project:
        filters["project"] = project
    grouped = {}
    for row in frappe.get_list("Task", filters=filters, fields=["pulse_release", "status"], limit_page_length=0):
        grouped.setdefault(row.pulse_release, []).append(row)
    return [{"release_name": name, **_progress(rows)} for name, rows in sorted(grouped.items())]


@frappe.whitelist()
def release_tasks(release, project=None):
    filters = {"pulse_release": release}
    if project:
        filters["project"] = project
    return frappe.get_list("Task", filters=filters, fields=TASK_FIELDS,
                          order_by="workflow_state asc, modified desc",
                          limit_page_length=0)


def _sprint(name, permission="read"):
    doc = frappe.get_doc("Pulse Sprint", name)
    doc.check_permission(permission)
    frappe.get_doc("Project", doc.project).check_permission(permission)
    return doc


@frappe.whitelist()
def move_to_sprint(tasks, sprint=None):
    """Atomic backlog/sprint planning; all documents are checked before writes."""
    names = frappe.parse_json(tasks) if isinstance(tasks, str) else tasks
    if not isinstance(names, list) or not names or len(names) > 200:
        frappe.throw("Select between 1 and 200 tasks.")
    return _move_to_sprint(names, sprint)


def _move_to_sprint(names, sprint=None):
    """Internal uncapped operation; caller controls its input and transaction."""
    target = _sprint(sprint, "write") if sprint else None
    if target and target.status == "Completed":
        frappe.throw("A completed sprint cannot accept tasks.")
    docs = [frappe.get_doc("Task", name) for name in dict.fromkeys(names)]
    for doc in docs:
        doc.check_permission("write")
        if doc.get("pulse_sprint"):
            source = _sprint(doc.pulse_sprint, "write")
            if source.status == "Completed":
                frappe.throw("Tasks in completed sprints cannot be moved.")
        if target and doc.project != target.project:
            frappe.throw("Task and sprint must belong to the same project.")
    for doc in docs:
        doc.pulse_sprint = sprint or None
        doc.save()
    return {"moved": [doc.name for doc in docs]}


@frappe.whitelist()
def sprint_progress(sprint):
    doc = _sprint(sprint)
    if doc.status == "Completed" and doc.get("closure_summary"):
        from pulse.api.sprint_history import require_full_history_access
        summary = frappe.parse_json(doc.closure_summary)
        require_full_history_access(set(summary.get("completed_task_ids", []) + summary.get("unfinished_task_ids", []) + summary.get("scope_added", []) + summary.get("scope_removed", [])), doc)
        return summary
    rows = frappe.get_list("Task", filters={"pulse_sprint": sprint, "pulse_archived": 0},
                           fields=["name", "subject", "status", "expected_time", "pulse_story_points"],
                           limit_page_length=0)
    total = len(rows)
    done = [row for row in rows if row.status == "Completed"]
    hours = sum(float(row.expected_time or 0) for row in rows)
    points = sum(float(row.pulse_story_points or 0) for row in rows)
    done_hours = sum(float(row.expected_time or 0) for row in done)
    done_points = sum(float(row.pulse_story_points or 0) for row in done)
    measure = doc.get("progress_measure") or "Tasks"
    planned, completed = {"Tasks": (total, len(done)), "Hours": (hours, done_hours),
                          "Points": (points, done_points)}[measure]
    return {"goal": doc.goal, "measure": measure, "planned": planned, "completed": completed,
            "percent": round(completed / planned * 100, 1) if planned else 0,
            "tasks": total, "completed_tasks": len(done), "estimated_hours": hours,
            "estimated_points": points, "completed_task_ids": [row.name for row in done],
            "unfinished_task_ids": [row.name for row in rows if row.status != "Completed"]}


@frappe.whitelist()
def close_sprint(sprint, unfinished="backlog", next_sprint=None):
    """Explicitly retain, return or transfer unfinished work and freeze the summary."""
    from pulse.api.sprint_history import read_events
    from frappe.utils import now_datetime
    doc = _sprint(sprint, "write")
    if doc.status != "Active":
        frappe.throw("Only an active sprint can be closed.")
    if unfinished not in ("backlog", "next", "retain"):
        frappe.throw("Choose backlog, next or retain for unfinished work.")
    if unfinished == "next" and (not next_sprint or next_sprint == sprint):
        frappe.throw("Choose a different destination sprint.")
    if unfinished == "next":
        target = _sprint(next_sprint, "write")
        if target.project != doc.project or target.status == "Completed":
            frappe.throw("Choose an unfinished sprint in the same project.")
    summary = sprint_progress(sprint)
    if summary["tasks"] != frappe.db.count("Task", {"pulse_sprint": sprint, "pulse_archived": 0}):
        frappe.throw("Closing requires access to every task in the sprint.")
    events = read_events(doc)
    baseline = {e['state']['task'] for e in events if e['kind'] == 'Baseline' and e['state']['present']}
    summary.update({"scope_added": sorted({e['state']['task'] for e in events if e['kind'] == 'Added'} - baseline),
                    "scope_removed": sorted({e['state']['task'] for e in events if e['kind'] in ('Removed', 'Deleted')}),
                    "unfinished_disposition": unfinished, "next_sprint": next_sprint if unfinished == "next" else None})
    # Freeze history before carryover moves; closing must not make incomplete
    # work appear burned down just because it was returned to the backlog.
    closed_at = now_datetime()
    if unfinished != "retain" and summary['unfinished_task_ids']:
        _move_to_sprint(summary['unfinished_task_ids'], next_sprint if unfinished == "next" else None)
    doc.closure_summary = frappe.as_json(summary)
    doc.closed_at = closed_at
    doc.status = "Completed"
    doc.flags.pulse_closing = True
    doc.save()
    return summary


@frappe.whitelist()
def configure_sprint(sprint, goal=None, progress_measure="Tasks", start=False):
    from frappe.utils import cint
    doc = _sprint(sprint, "write")
    if doc.status == "Completed":
        frappe.throw("Completed sprint settings are frozen.")
    if progress_measure not in ("Tasks", "Hours", "Points"):
        frappe.throw("Choose Tasks, Hours or Points.")
    doc.goal = goal
    doc.progress_measure = progress_measure
    if cint(start):
        if not doc.start_date or not doc.end_date:
            frappe.throw("Set the sprint start and end dates before starting.")
        doc.status = "Active"
    doc.save()
    return {"name": doc.name, "status": doc.status}
