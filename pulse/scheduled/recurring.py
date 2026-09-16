"""Recurring task automation.

Each active Pulse Recurring Task whose `next_run` has arrived spawns a real Task
in the "To Do" column (so it's actionable, not buried in Backlog), then its
`next_run` advances by one interval.
"""

import frappe
from frappe.utils import getdate, today


def generate_due():
    """Scheduler entrypoint (daily): generate tasks for every due template."""
    due = frappe.get_all(
        "Pulse Recurring Task",
        filters={"is_active": 1, "next_run": ["<=", today()]},
        pluck="name",
    )
    for name in due:
        try:
            generate_one(name, catch_up=True)
        except Exception:
            frappe.log_error(title="Pulse: recurring task generation failed",
                             message=frappe.get_traceback())


def generate_one(template, catch_up=False):
    """Create one Task from a template and advance next_run.

    catch_up=True keeps generating while next_run stays in the past so a template
    that missed several cycles produces the right number of tasks (bounded)."""
    doc = frappe.get_doc("Pulse Recurring Task", template)
    made = []
    guard = 0
    while True:
        guard += 1
        task = _spawn_task(doc)
        made.append(task)
        doc.last_generated = today()
        doc.advance_next_run()
        if not catch_up or getdate(doc.next_run) > getdate(today()) or guard >= 60:
            break
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return made


def _spawn_task(doc):
    from pulse.api.task_config import CATEGORY_STATUS, statuses_for

    statuses = statuses_for(doc.project)
    state = next((row for row in statuses if row["category"] == "To Do"), None)
    state = state or next((row for row in statuses if row["category"] not in ("Done", "Cancelled")), None)
    if not state:
        frappe.throw("Recurring tasks require an open status in the project.")
    task = frappe.get_doc({
        "doctype": "Task",
        "subject": doc.subject,
        "project": doc.project,
        "type": doc.task_type,
        "priority": doc.priority or "Medium",
        "description": doc.description,
        "pulse_recurring": doc.name,
        "workflow_state": state["label"],
        "status": CATEGORY_STATUS[state["category"]],
        "exp_end_date": doc.next_run,
    })
    task.insert(ignore_permissions=True)

    if doc.assign_to:
        try:
            from frappe.desk.form.assign_to import add as assign_add
            assign_add({"assign_to": [doc.assign_to], "doctype": "Task", "name": task.name})
        except Exception:
            frappe.log_error(title="Pulse: recurring assign failed",
                             message=frappe.get_traceback())

    try:
        from pulse.api.audit import log
        log("Task Created", "Task", task.name, doc.project,
            f"Recurring: {doc.subject[:120]}")
    except Exception:
        pass
    return task.name
