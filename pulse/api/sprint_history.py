"""Append-only sprint snapshots; never infer past membership from current tasks."""
import json
import frappe
from frappe.utils import cint, flt, now_datetime


def snapshot(doc, present=True):
    # Retain the fields native role/user permissions need after physical deletion.
    access = {field.fieldname: doc.get(field.fieldname) for field in doc.meta.fields
              if field.fieldtype == "Link"}
    access.update({"doctype": "Task", "name": doc.name, "owner": doc.owner,
                   "_assign": doc.get("_assign"), "project": doc.project})
    return {"task": doc.name, "subject": doc.subject,
            "present": bool(present) and not cint(doc.get("pulse_archived")),
            "completed": doc.status == "Completed", "hours": flt(doc.get("expected_time")),
            "points": flt(doc.get("pulse_story_points")), "access": access}


def append_event(sprint, state, kind="Changed"):
    if not sprint or (kind != "Deleted" and frappe.db.get_value("Pulse Sprint", sprint, "status") == "Completed"):
        return
    frappe.get_doc({"doctype": "Pulse Sprint Event", "sprint": sprint,
                    "task_id": state["task"], "event_kind": kind,
                    "occurred_at": now_datetime(), "snapshot": json.dumps(state)}).insert(ignore_permissions=True)


def record_task_change(doc, method=None):
    old = doc.get_doc_before_save()
    previous = old.get("pulse_sprint") if old else None
    current = doc.get("pulse_sprint")
    if current:
        project, status = frappe.db.get_value("Pulse Sprint", current, ["project", "status"])
        if project != doc.project:
            frappe.throw("Task and sprint must belong to the same project.")
        if current != previous and status == "Completed":
            frappe.throw("A completed sprint cannot accept tasks.")
    if previous and previous != current and frappe.db.get_value("Pulse Sprint", previous, "status") == "Completed":
        frappe.throw("Tasks in completed sprints cannot be moved.")
    if frappe.flags.get("pulse_migration"):
        return
    if previous != current:
        from pulse.api.planning import _sprint
        for name in {previous, current} - {None, ""}:
            _sprint(name, "write")
    if previous and previous != current:
        append_event(previous, snapshot(old, False), "Removed")
    if current and (not old or previous != current or snapshot(old) != snapshot(doc)):
        before_present = bool(old and previous == current and not cint(old.get("pulse_archived")))
        after_present = not cint(doc.get("pulse_archived"))
        kind = "Added" if after_present and not before_present else "Removed" if before_present and not after_present else "Changed"
        append_event(current, snapshot(doc), kind)
    if (old and cint(old.get("pulse_archived")) != cint(doc.get("pulse_archived"))) or (previous and not current):
        for name in {previous, current} - {None, ""}:
            frappe.get_doc("Pulse Sprint", name).recalculate_tasks()


def record_task_deletion(doc, method=None):
    if frappe.flags.get("pulse_migration"):
        return
    sprints = set(frappe.get_all("Pulse Sprint Event", filters={"task_id": doc.name}, pluck="sprint"))
    if doc.get("pulse_sprint"):
        sprints.add(doc.pulse_sprint)
    for sprint in sprints:
        append_event(sprint, snapshot(doc, False), "Deleted")


def baseline(sprint):
    for name in frappe.get_all("Task", filters={"pulse_sprint": sprint.name}, pluck="name"):
        append_event(sprint.name, snapshot(frappe.get_doc("Task", name)), "Baseline")


def read_events(sprint):
    sprint.check_permission("read")
    frappe.get_doc("Project", sprint.project).check_permission("read")
    filters = {"sprint": sprint.name}
    if sprint.get("closed_at"):
        filters["occurred_at"] = ["<=", sprint.closed_at]
    rows = frappe.get_all("Pulse Sprint Event", filters=filters,
                          fields=["occurred_at", "snapshot", "event_kind"],
                          order_by="occurred_at asc, creation asc, name asc", limit_page_length=0)
    if sprint.get("history_started_at"):
        from frappe.utils import get_datetime
        rows = [row for row in rows if get_datetime(row.occurred_at) >= get_datetime(sprint.history_started_at)]
    task_ids = {json.loads(row.snapshot)["task"] for row in rows}
    require_full_history_access(task_ids, sprint)
    return [{"at": str(row.occurred_at), "kind": row.event_kind,
             "state": json.loads(row.snapshot)} for row in rows]


def require_full_history_access(task_ids, sprint=None):
    """Never leak a hidden task through historical aggregates or frozen outcomes."""
    if not task_ids or frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
        return
    visible = set(frappe.get_list("Task", filters={"name": ["in", list(task_ids)]}, pluck="name", limit_page_length=0))
    existing = set(frappe.get_all("Task", filters={"name": ["in", list(task_ids)]}, pluck="name"))
    if visible != existing:
        frappe.throw("This historical report requires access to every task in its history.", frappe.PermissionError)
    deleted = set(task_ids) - existing
    if not deleted:
        return
    # Tombstones survive closure cutoffs but never alter the frozen chart/summary.
    tombstones = frappe.get_all("Pulse Sprint Event",
        filters={"sprint": sprint.name if sprint else "", "task_id": ["in", list(deleted)], "event_kind": "Deleted"},
        fields=["task_id", "snapshot"], order_by="occurred_at desc")
    access_by_task = {row.task_id: json.loads(row.snapshot).get("access") for row in tombstones}
    for task_id in deleted:
        access = access_by_task.get(task_id)
        if not access or not frappe.has_permission("Task", "read", doc=frappe.get_doc(access)):
            frappe.throw("This historical report requires access to every task in its history.", frappe.PermissionError)


def initialize_active_history():
    """Migration baseline at observation time; intentionally do not invent older days."""
    for name in frappe.get_all("Pulse Sprint", filters={"status": "Active"}, pluck="name"):
        doc = frappe.get_doc("Pulse Sprint", name)
        if not doc.get("history_started_at"):
            doc.db_set("history_started_at", now_datetime(), update_modified=False)
            baseline(doc)
