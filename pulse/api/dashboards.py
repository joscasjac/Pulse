"""Pulse — per-user customizable dashboards API.

Canonical namespace: pulse.api.dashboards.*

Every user gets their own editable dashboard. On first open we clone the admin
default template (or a built-in starter) into a personal Pulse Dashboard the user
then fully controls (add / move / resize / remove widgets).
"""

import json
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import today

MANAGER_ROLES = {"Pulse Admin", "Pulse Manager", "System Manager"}

# Built-in starter layout used when no admin default template exists.
STARTER_WIDGETS = [
    {"widget_type": "Number Card", "title": "My Open Tasks", "metric": "my_tasks",
     "x": 0, "y": 0, "w": 3, "h": 2, "color": "#3b82f6"},
    {"widget_type": "Number Card", "title": "Overdue", "metric": "overdue",
     "x": 3, "y": 0, "w": 3, "h": 2, "color": "#ef4444"},
    {"widget_type": "Number Card", "title": "Active Projects", "metric": "active_projects",
     "x": 6, "y": 0, "w": 3, "h": 2, "color": "#22c55e"},
    {"widget_type": "Number Card", "title": "Hours This Week", "metric": "hours_this_week",
     "x": 9, "y": 0, "w": 3, "h": 2, "color": "#f97316"},
    {"widget_type": "My Tasks", "title": "My Work", "metric": "my_tasks",
     "x": 0, "y": 2, "w": 6, "h": 5},
    {"widget_type": "Sprint Burndown", "title": "Active Sprint Burndown", "metric": "burndown",
     "chart_type": "Line", "x": 6, "y": 2, "w": 6, "h": 5},
    {"widget_type": "Activity Feed", "title": "Recent Activity", "metric": "activity",
     "x": 0, "y": 7, "w": 6, "h": 4},
    {"widget_type": "Workload", "title": "Team Workload", "metric": "workload",
     "chart_type": "Bar", "x": 6, "y": 7, "w": 6, "h": 4},
]

# Catalog offered in the "add widget" palette.
WIDGET_CATALOG = [
    {"widget_type": "Number Card", "label": "KPI Number", "metrics": [
        "my_tasks", "overdue", "due_today", "in_progress", "completed_today",
        "active_projects", "total_open", "blocked", "hours_this_week"]},
    {"widget_type": "My Tasks", "label": "My Tasks list", "metrics": ["my_tasks"]},
    {"widget_type": "Task List", "label": "Task list (filtered)", "metrics": ["tasks"]},
    {"widget_type": "Sprint Burndown", "label": "Sprint Burndown", "metrics": ["burndown"]},
    {"widget_type": "Velocity", "label": "Velocity", "metrics": ["velocity"]},
    {"widget_type": "Workload", "label": "Team Workload", "metrics": ["workload"]},
    {"widget_type": "Activity Feed", "label": "Activity Feed", "metrics": ["activity"]},
    {"widget_type": "OKR Progress", "label": "OKR Progress", "metrics": ["okr"]},
    {"widget_type": "Risk Matrix", "label": "Risk Matrix", "metrics": ["risk"]},
    {"widget_type": "Chart", "label": "Custom Chart", "metrics": ["tasks_by_state", "tasks_by_type"]},
    {"widget_type": "Text Note", "label": "Text / Markdown note", "metrics": []},
]


def _is_manager(user):
    return bool(set(frappe.get_roles(user)) & MANAGER_ROLES)


def _serialize(dashboard):
    return {
        "name": dashboard.name,
        "dashboard_name": dashboard.dashboard_name,
        "owner_user": dashboard.owner_user,
        "scope": dashboard.scope,
        "is_default": dashboard.is_default,
        "project": dashboard.project,
        "layout_json": dashboard.layout_json,
        "widgets": [
            {
                "widget_type": w.widget_type, "title": w.title, "metric": w.metric,
                "chart_type": w.chart_type, "x": w.x, "y": w.y, "w": w.w, "h": w.h,
                "color": w.color, "filters_json": w.filters_json, "config_json": w.config_json,
            }
            for w in dashboard.widgets
        ],
    }


def _find_default_template():
    names = frappe.get_list("Pulse Dashboard", filters={"is_default": 1, "scope": ["!=", "Personal"]}, pluck="name", limit_page_length=1)
    return frappe.get_doc("Pulse Dashboard", names[0]) if names else None



@frappe.whitelist()
def get_my_dashboard():
    """Return the current user's personal dashboard, creating it on first use."""
    user = frappe.session.user
    name = frappe.db.get_value(
        "Pulse Dashboard", {"owner_user": user, "scope": "Personal"}, "name"
    )
    if name:
        return _serialize(frappe.get_doc("Pulse Dashboard", name))

    # First open: clone the admin default template, else the built-in starter.
    template = _find_default_template()
    widgets = (
        [w.as_dict() for w in template.widgets] if template else list(STARTER_WIDGETS)
    )
    doc = frappe.get_doc({
        "doctype": "Pulse Dashboard",
        "dashboard_name": "My Dashboard",
        "owner_user": user,
        "scope": "Personal",
        "widgets": widgets,
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return _serialize(doc)


@frappe.whitelist()
def save_dashboard(widgets=None, layout_json=None, dashboard_name=None):
    """Persist the current user's dashboard layout (widgets + positions)."""
    user = frappe.session.user
    if isinstance(widgets, str):
        widgets = json.loads(widgets or "[]")
    widgets = widgets or []

    name = frappe.db.get_value(
        "Pulse Dashboard", {"owner_user": user, "scope": "Personal"}, "name"
    )
    if name:
        doc = frappe.get_doc("Pulse Dashboard", name)
    else:
        doc = frappe.get_doc({
            "doctype": "Pulse Dashboard", "owner_user": user, "scope": "Personal",
            "dashboard_name": dashboard_name or "My Dashboard",
        })

    if dashboard_name:
        doc.dashboard_name = dashboard_name
    if layout_json is not None:
        doc.layout_json = layout_json

    doc.set("widgets", [])
    for w in widgets:
        doc.append("widgets", {
            "widget_type": w.get("widget_type"), "title": w.get("title"),
            "metric": w.get("metric"), "chart_type": w.get("chart_type"),
            "x": w.get("x") or 0, "y": w.get("y") or 0,
            "w": w.get("w") or 4, "h": w.get("h") or 3,
            "color": w.get("color"),
            "filters_json": w.get("filters_json"), "config_json": w.get("config_json"),
        })
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _serialize(doc)


@frappe.whitelist()
def reset_dashboard():
    """Delete the user's personal dashboard so it re-seeds from the default template."""
    user = frappe.session.user
    name = frappe.db.get_value(
        "Pulse Dashboard", {"owner_user": user, "scope": "Personal"}, "name"
    )
    if name:
        frappe.delete_doc("Pulse Dashboard", name, ignore_permissions=True, force=True)
        frappe.db.commit()
    return get_my_dashboard()


@frappe.whitelist()
def get_widget_catalog():
    """Return the palette of widget types + their available metrics."""
    return WIDGET_CATALOG


@frappe.whitelist()
def get_dashboard_stats(user=None):
    """KPI stats for dashboard number cards (standalone Pulse data)."""
    if user and user != frappe.session.user:
        frappe.throw(_("Dashboard statistics are scoped to the signed-in user."), frappe.PermissionError)
    user = frappe.session.user
    day = today()
    tasks = frappe.get_list("Task", fields=["name", "status", "workflow_state", "exp_end_date", "modified", "_assign"], limit_page_length=0)
    open_tasks = [t for t in tasks if t.status not in ("Completed", "Cancelled")]
    from pulse.api.time import get_user_hours
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
    return {
        "my_tasks": sum(user in (frappe.parse_json(t._assign or "[]") or []) for t in open_tasks),
        "in_progress": sum(t.workflow_state == "In Progress" for t in open_tasks),
        "completed_today": sum(t.status == "Completed" and str(t.modified)[:10] == day for t in tasks),
        "overdue": sum(bool(t.exp_end_date) and str(t.exp_end_date)[:10] < day for t in open_tasks),
        "due_today": sum(str(t.exp_end_date)[:10] == day for t in open_tasks),
        "active_projects": len(frappe.get_list("Project", filters={"status": "Open"}, pluck="name", limit_page_length=0)),
        "total_open": len(open_tasks),
        "blocked": sum(t.workflow_state == "Blocked" for t in open_tasks),
        "hours_this_week": get_user_hours(from_date=week_start),
    }


@frappe.whitelist()
def get_dashboard_series():
    """Aggregate only records readable by the current user."""
    tasks = frappe.get_list("Task", fields=["status", "workflow_state", "type", "_assign", "pulse_sprint"], limit_page_length=0)
    def group_count(field):
        counts = {}
        for task in tasks:
            if task.get(field):
                counts[task[field]] = counts.get(task[field], 0) + 1
        return [{"label": k, "value": v} for k, v in sorted(counts.items(), key=lambda item: -item[1])]
    workload = {}
    for task in tasks:
        if task.status in ("Completed", "Cancelled"):
            continue
        for user in frappe.parse_json(task._assign or "[]") or []:
            workload[user] = workload.get(user, 0) + 1
    velocity = [{"label": s.sprint_name or s.name,
                 "value": sum(t.status == "Completed" and t.pulse_sprint == s.name for t in tasks)}
                for s in frappe.get_list("Pulse Sprint", fields=["name", "sprint_name"], order_by="start_date asc", limit_page_length=0)]
    return {"tasks_by_state": group_count("workflow_state"), "tasks_by_type": group_count("type"),
            "workload": [{"label": k.split("@")[0], "value": v} for k, v in sorted(workload.items(), key=lambda item: -item[1])[:8]],
            "velocity": velocity}


@frappe.whitelist()
def set_default_template(name):
    """Admin/Manager: mark a shared dashboard as the org default template."""
    if not _is_manager(frappe.session.user):
        frappe.throw(_("Only Pulse Admins or Managers can set the default dashboard."))
    from pulse.hooks.permissions import require_permission
    dashboard = require_permission("Pulse Dashboard", name, "write")
    if dashboard.scope == "Personal":
        frappe.throw(_("Share the dashboard before making it the default."))
    for other in frappe.get_list("Pulse Dashboard", filters={"is_default": 1}, pluck="name"):
        if other != name:
            frappe.db.set_value("Pulse Dashboard", other, "is_default", 0)
    frappe.db.set_value("Pulse Dashboard", name, "is_default", 1)
    frappe.db.commit()
    return {"ok": True, "default": name}
