"""Pulse recurring tasks (canonical namespace: pulse.api.recurring.*).

Templates that auto-generate real Tasks on a schedule. The heavy lifting (task
creation + next_run advance) lives in pulse.scheduled.recurring.
"""

import json

import frappe
from frappe.utils import today


def _cadence(count, unit):
    count = int(count or 1)
    unit = (unit or "Week").lower()
    return f"every {unit}" if count == 1 else f"every {count} {unit}s"


@frappe.whitelist()
def list_recurring(project=None):
    filters = {}
    if project:
        filters["project"] = project
    rows = frappe.get_all(
        "Pulse Recurring Task", filters=filters,
        fields=["name", "subject", "project", "task_type", "priority", "assign_to",
                "story_points", "interval_count", "interval_unit", "start_date",
                "next_run", "last_generated", "is_active", "description"],
        order_by="is_active desc, next_run asc",
    )
    for r in rows:
        r["cadence"] = _cadence(r["interval_count"], r["interval_unit"])
    return rows


@frappe.whitelist()
def create_recurring(subject, project, interval_count=1, interval_unit="Week",
                     priority="Medium", task_type=None, story_points=0,
                     assign_to=None, description=None, start_date=None,
                     generate_now=1):
    """Create a recurring template. By default generates the first task at once."""
    doc = frappe.get_doc({
        "doctype": "Pulse Recurring Task",
        "subject": subject,
        "project": project,
        "interval_count": int(interval_count or 1),
        "interval_unit": interval_unit or "Week",
        "priority": priority or "Medium",
        "task_type": task_type,
        "story_points": float(story_points or 0),
        "assign_to": assign_to,
        "description": description,
        "start_date": start_date or today(),
    })
    doc.insert()
    frappe.db.commit()

    generated = []
    if int(generate_now or 0):
        from pulse.scheduled.recurring import generate_one
        generated = generate_one(doc.name, catch_up=False)
    # re-read: generate_one advanced next_run on a fresh copy of the doc
    next_run = frappe.db.get_value("Pulse Recurring Task", doc.name, "next_run")
    return {"name": doc.name, "next_run": next_run, "generated": generated}


@frappe.whitelist()
def update_recurring(name, **fields):
    doc = frappe.get_doc("Pulse Recurring Task", name)
    allowed = {"subject", "project", "task_type", "priority", "assign_to",
               "story_points", "interval_count", "interval_unit", "start_date",
               "next_run", "description"}
    for k, v in fields.items():
        if k in allowed:
            doc.set(k, v)
    doc.save()
    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist()
def toggle_recurring(name, is_active):
    active = 1 if str(is_active) in ("1", "true", "True") else 0
    frappe.db.set_value("Pulse Recurring Task", name, "is_active", active)
    frappe.db.commit()
    return {"name": name, "is_active": active}


@frappe.whitelist()
def delete_recurring(name):
    frappe.delete_doc("Pulse Recurring Task", name, ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def generate_now(name):
    """Manually spawn the next task from a template now."""
    from pulse.scheduled.recurring import generate_one
    return {"generated": generate_one(name, catch_up=False)}
