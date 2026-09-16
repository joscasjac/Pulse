"""Transactional migration to native drafts; retain all legacy source records.

Date-only rows receive deterministic intervals in source creation/row order.
Run ``bench execute pulse.services.time_migration.migrate`` to preview validation.
"""
from datetime import timedelta
import math

import frappe
from frappe.utils import get_datetime


def migrate(dry_run=True):
    frappe.only_for("System Manager")
    dry_run = frappe.utils.cint(dry_run)
    default_company = frappe.db.get_single_value("Global Defaults", "default_company")
    result = {"migrated": [], "already_migrated": [], "dry_run": bool(dry_run)}
    cursors = {}
    plan = []
    frappe.db.savepoint("pulse_native_time_migration")
    try:
        # Serialize migration runs before checking unique child provenance. Native
        # unique constraints remain the final guard against concurrent insertions.
        names = frappe.db.sql("SELECT name FROM `tabPulse Timesheet` ORDER BY creation, name FOR UPDATE", pluck=True)
        for name in names:
            old = frappe.get_doc("Pulse Timesheet", name)
            by_company = {}
            for row in old.entries:
                hours = float(row.hours or 0)
                if not math.isfinite(hours) or hours <= 0 or hours > 24:
                    frappe.throw(f"Legacy entry {row.name} has invalid hours; correct it before migration.")
                if not row.date:
                    frappe.throw(f"Legacy entry {row.name} needs a date before migration.")
                # Advance even for previously migrated rows so partial retries keep
                # subsequent rows at their original deterministic intervals.
                key = (old.user, str(row.date))
                midnight = get_datetime(str(row.date) + " 00:00:00")
                start = cursors.get(key, midnight)
                end = start + timedelta(hours=hours)
                if end > midnight + timedelta(days=1):
                    frappe.throw(f"More than 24 legacy hours for {old.user} on {row.date}; resolve before migration.")
                cursors[key] = end
                if frappe.db.exists("Timesheet Detail", {"pulse_legacy_entry": row.name}):
                    result["already_migrated"].append(row.name)
                    continue
                project = row.project
                if row.task:
                    if not frappe.db.exists("Task", row.task):
                        frappe.throw(f"Legacy entry {row.name} needs a valid native Task before migration.")
                    project = frappe.db.get_value("Task", row.task, "project")
                if project and not frappe.db.exists("Project", project):
                    frappe.throw(f"Legacy entry {row.name} needs a valid native Project before migration.")
                company = (frappe.db.get_value("Project", project, "company") if project else None) or default_company
                if not company:
                    frappe.throw(f"Configure a company for legacy entry {row.name} before migration.")
                description = row.description or ""
                activity = row.get("activity_type")
                native_activity = activity if activity and frappe.db.exists("Activity Type", activity) else None
                if activity and not native_activity:
                    description += f"\nLegacy activity: {activity}"
                by_company.setdefault(company, []).append({
                    "task": row.task, "project": project, "from_time": start, "to_time": end,
                    "hours": hours, "is_billable": row.billable, "pulse_legacy_entry": row.name,
                    "activity_type": native_activity, "description": description})
            for company, entries in by_company.items():
                plan.append((old, company, entries))
        for old, company, entries in plan:
            doc = frappe.get_doc({"doctype": "Timesheet", "user": old.user, "company": company,
                                  "pulse_legacy_timesheet": old.name,
                                  "note": "Migrated from Pulse Timesheet. Original status: " + str(old.status)
                                          + ". Clock intervals synthesized from date-only records; original records retained.",
                                  "time_logs": entries})
            # Administrator-run migration bypasses access only. Native document
            # validation, overlap checks, and financial constraints stay enabled.
            doc.insert(ignore_permissions=True)
            result["migrated"].append({"legacy": old.name, "timesheet": doc.name,
                                       "company": company, "hours": sum(r["hours"] for r in entries)})
        if dry_run:
            frappe.db.rollback(save_point="pulse_native_time_migration")
    except Exception:
        frappe.db.rollback(save_point="pulse_native_time_migration")
        raise
    return result
