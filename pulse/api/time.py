"""Time tracking on native ERPNext Timesheet / Timesheet Detail records."""
from datetime import timedelta
import math

import frappe
from frappe.utils import get_datetime, getdate, now_datetime, today
from pulse.hooks.permissions import require_permission


def _resolve(task):
    from pulse.api.spa import resolve_task
    name = resolve_task(task)
    return require_permission("Task", name)


def _self(user=None):
    user = user or frappe.session.user
    if user == "Guest" or user != frappe.session.user:
        frappe.throw("Time can only be recorded or requested for the signed-in user.", frappe.PermissionError)
    return user


def _hours(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        frappe.throw("Hours must be a finite positive number.")
    if not math.isfinite(result) or result <= 0 or result > 24:
        frappe.throw("Hours must be greater than zero and no more than 24 per entry.")
    return result


def _entries(task=None, user=None, from_date=None):
    filters = {"docstatus": ["<", 2]}
    if user:
        filters["user"] = user
    records = frappe.get_list("Timesheet", filters=filters, pluck="name", limit_page_length=0)
    visible_tasks = set(frappe.get_list("Task", pluck="name", limit_page_length=0))
    rows = []
    for name in records:
        doc = require_permission("Timesheet", name)
        for row in doc.time_logs:
            if (row.task and row.task not in visible_tasks) or (task and row.task != task):
                continue
            if from_date and getdate(row.from_time) < getdate(from_date):
                continue
            rows.append({"name": row.name, "timesheet": doc.name, "date": str(getdate(row.from_time)),
                         "from_time": row.from_time, "to_time": row.to_time,
                         "hours": float(row.hours or 0), "description": row.description,
                         "user": doc.user, "billable": bool(row.is_billable),
                         "docstatus": doc.docstatus, "task": row.task, "project": row.project})
    return sorted(rows, key=lambda r: str(r["from_time"]), reverse=True)


@frappe.whitelist()
def log_time(task, hours, date=None, note=None, user=None, from_time=None,
             billable=0, activity_type=None):
    """Create a native draft timesheet; ERPNext validates interval overlap and links."""
    user = _self(user)
    task_doc = _resolve(task)
    hours = _hours(hours)
    start = get_datetime(from_time or (str(getdate(date or today())) + " 00:00:00"))
    end = start + timedelta(hours=hours)
    project = require_permission("Project", task_doc.project) if task_doc.project else None
    company = project.get("company") if project else None
    if not company:
        company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        frappe.throw("Configure an ERPNext company before recording time.")
    doc = frappe.get_doc({
        "doctype": "Timesheet", "user": user, "company": company,
        "time_logs": [{"task": task_doc.name, "project": task_doc.project,
                       "from_time": start, "to_time": end, "hours": hours,
                       "description": note, "is_billable": frappe.utils.cint(billable),
                       "activity_type": activity_type}],
    })
    doc.insert()
    return {"ok": True, "task": task_doc.name, "issue_key": task_doc.get("issue_key"),
            "timesheet": doc.name, "logged": hours, "total_hours": get_task_time(task_doc.name)}


@frappe.whitelist()
def get_task_time(task):
    doc = _resolve(task)
    return sum(r["hours"] for r in _entries(task=doc.name))


@frappe.whitelist()
def get_task_time_detail(task):
    doc = _resolve(task)
    return _entries(task=doc.name)


def get_user_hours(from_date, user=None):
    return sum(r["hours"] for r in _entries(user=_self(user), from_date=from_date))


@frappe.whitelist()
def get_time_summary(task):
    doc = _resolve(task)
    entries = _entries(task=doc.name)
    actual = sum(r["hours"] for r in entries)
    billable = sum(r["hours"] for r in entries if r["billable"])
    return {"estimated_hours": float(doc.get("expected_time") or 0), "actual_hours": actual,
            "billable_hours": billable, "nonbillable_hours": actual - billable,
            "entries": entries, "scope": "permitted_timesheets",
            "draft_hours": sum(r["hours"] for r in entries if r["docstatus"] == 0),
            "submitted_hours": sum(r["hours"] for r in entries if r["docstatus"] == 1)}


@frappe.whitelist()
def my_tasks(status=None, limit=100):
    me = _self()
    rows = frappe.get_list(
        "Task", filters={"status": status or ["not in", ["Completed", "Cancelled"]]},
        fields=["name", "issue_key", "subject", "status", "workflow_state", "project", "priority", "_assign"],
        order_by="modified desc", limit_page_length=0)
    assigned = [r for r in rows if me in (frappe.parse_json(r.pop("_assign", None) or "[]") or [])]
    return assigned[:max(1, min(int(limit), 500))]


@frappe.whitelist()
def get_timer():
    user = _self()
    if not frappe.db.exists("Pulse Timer", user):
        return None
    timer = require_permission("Pulse Timer", user)
    if not frappe.has_permission("Task", "read", doc=timer.task):
        return {"restricted": True, "started_at": timer.started_at, "billable": timer.billable}
    return {"task": timer.task, "started_at": timer.started_at, "billable": timer.billable}


@frappe.whitelist()
def start_timer(task, billable=0):
    user = _self()
    doc = _resolve(task)
    if frappe.db.exists("Pulse Timer", user):
        frappe.throw("Stop your current timer before starting another.")
    # User is the primary key: simultaneous starts cannot create two timers.
    timer = frappe.get_doc({"doctype": "Pulse Timer", "user": user, "task": doc.name,
                            "started_at": now_datetime(), "billable": frappe.utils.cint(billable)})
    timer.insert()
    return get_timer()


@frappe.whitelist()
def stop_timer(note=None):
    user = _self()
    # Serialize stop requests so the same interval cannot be logged twice.
    rows = frappe.db.sql("SELECT name FROM `tabPulse Timer` WHERE name=%s FOR UPDATE", (user,))
    if not rows:
        frappe.throw("No timer is running.")
    timer = require_permission("Pulse Timer", user, "write")
    elapsed = (now_datetime() - get_datetime(timer.started_at)).total_seconds() / 3600
    if elapsed <= 0:
        frappe.throw("No time has elapsed yet. Wait a moment before stopping the timer.")
    if elapsed > 24:
        frappe.throw("This timer exceeds 24 hours. Discard it and add reviewed daily entries; no time has been saved.")
    result = log_time(timer.task, elapsed, from_time=timer.started_at,
                      note=note, billable=timer.billable)
    frappe.delete_doc("Pulse Timer", user)
    return result


@frappe.whitelist()
def discard_timer():
    user = _self()
    require_permission("Pulse Timer", user, "delete")
    frappe.delete_doc("Pulse Timer", user)
    return {"ok": True}


@frappe.whitelist()
def get_my_time(from_date=None):
    """Only native records visible to the current user, including non-task work."""
    entries = _entries(user=_self(), from_date=from_date)
    return {"entries": entries, "scope": "permitted_timesheets",
            "total_hours": sum(row["hours"] for row in entries),
            "draft_hours": sum(row["hours"] for row in entries if row["docstatus"] == 0),
            "submitted_hours": sum(row["hours"] for row in entries if row["docstatus"] == 1)}
