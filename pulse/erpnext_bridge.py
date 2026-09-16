"""Pulse ↔ ERPNext Projects consolidation.

Makes ERPNext Project/Task the single source of truth: adds the few custom
fields Pulse needs, and migrates existing Pulse Project/Task (and related
records) into the ERPNext doctypes, re-pointing all retained Pulse doctypes.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


# ---------------------------------------------------------------------------
# Custom fields — the Pulse extensions on ERPNext Task / Project
# ---------------------------------------------------------------------------

# The Pulse extensions on ERPNext Task / Project. These carry the agile data that
# lived on the old standalone Pulse Task/Project doctypes. Fields ERPNext already
# provides natively (description, parent_task, is_milestone, holiday_list, users,
# type) are intentionally omitted.
CUSTOM_FIELDS = {
    "Timesheet Detail": [
        {"fieldname": "pulse_legacy_entry", "label": "Legacy Pulse Entry", "fieldtype": "Data",
         "read_only": 1, "unique": 1, "hidden": 1},
    ],
    "Timesheet": [
        {"fieldname": "pulse_legacy_timesheet", "label": "Legacy Pulse Timesheet", "fieldtype": "Data",
         "read_only": 1, "search_index": 1},
    ],
    "Task": [
        {"fieldname": "pulse_legacy_task", "label": "Legacy Pulse Task", "fieldtype": "Data",
         "unique": 1, "read_only": 1, "hidden": 1},
        {"fieldname": "pulse_labels", "label": "Labels", "fieldtype": "Table",
         "options": "Pulse Task Label", "insert_after": "pulse_release"},
        {"fieldname": "pulse_archived", "label": "Archived", "fieldtype": "Check",
         "default": "0", "insert_after": "pulse_labels"},
        {"fieldname": "pulse_story_points", "label": "Story Points", "fieldtype": "Float",
         "non_negative": 1, "insert_after": "expected_time"},
        {"fieldname": "issue_key", "label": "Issue Key", "fieldtype": "Data",
         "read_only": 1, "unique": 1, "in_list_view": 1, "search_index": 1,
         "insert_after": "subject"},
        {"fieldname": "seq", "label": "Sequence", "fieldtype": "Int",
         "read_only": 1, "hidden": 1, "insert_after": "issue_key"},
        # Project-specific board names are validated by pulse.api.task_config.
        {"fieldname": "workflow_state", "label": "Board State", "fieldtype": "Data",
         "in_standard_filter": 1, "insert_after": "status"},
        {"fieldname": "pulse_sprint", "label": "Sprint", "fieldtype": "Link",
         "options": "Pulse Sprint", "insert_after": "workflow_state"},
        {"fieldname": "pulse_epic", "label": "Epic", "fieldtype": "Link",
         "options": "Task", "insert_after": "pulse_sprint"},
        {"fieldname": "pulse_rank", "label": "Board Rank", "fieldtype": "Int",
         "insert_after": "pulse_epic"},
        {"fieldname": "pulse_release", "label": "Release", "fieldtype": "Data",
         "insert_after": "pulse_rank"},
        {"fieldname": "pulse_recurring", "label": "Recurring Template", "fieldtype": "Link",
         "options": "Pulse Recurring Task", "read_only": 1, "insert_after": "pulse_release"},
    ],
    "Project": [
        {"fieldname": "pulse_legacy_project", "label": "Legacy Pulse Project", "fieldtype": "Data",
         "unique": 1, "read_only": 1, "hidden": 1},
        {"fieldname": "pulse_is_template", "label": "Project Template", "fieldtype": "Check",
         "default": "0", "insert_after": "project_name"},
        {"fieldname": "pulse_task_statuses", "label": "Task Statuses", "fieldtype": "Table",
         "options": "Pulse Task Status", "insert_after": "pulse_board_type"},
        {"fieldname": "pulse_task_types", "label": "Task Types", "fieldtype": "Table",
         "options": "Pulse Project Task Type", "insert_after": "pulse_task_statuses"},
        {"fieldname": "pulse_project_key", "label": "Project Key", "fieldtype": "Data",
         "insert_after": "project_name"},
        {"fieldname": "pulse_enable_scrum", "label": "Enable Scrum", "fieldtype": "Check",
         "insert_after": "pulse_project_key"},
        {"fieldname": "pulse_board_type", "label": "Board Type", "fieldtype": "Select",
         "options": "Scrum\nKanban", "default": "Scrum",
         "insert_after": "pulse_enable_scrum"},
        {"fieldname": "pulse_default_sprint_length", "label": "Default Sprint Length (days)",
         "fieldtype": "Int", "default": "14", "insert_after": "pulse_board_type"},
        {"fieldname": "task_counter", "label": "Task Counter", "fieldtype": "Int",
         "hidden": 1, "read_only": 1, "default": "0",
         "insert_after": "pulse_default_sprint_length"},
    ],
}


def ensure_custom_fields():
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)


def ensure_default_company():
    """ERPNext Project requires a Company. Make sure any existing company is set
    as the site default so new Pulse projects inherit it automatically.

    We deliberately do NOT create a Company here: a valid ERPNext Company needs
    warehouse types, fiscal year, etc. that only the ERPNext setup wizard scaffolds.
    Returns the default company name, or None if ERPNext setup hasn't been done."""
    company = _default_company()
    if company and not frappe.db.get_single_value("Global Defaults", "default_company"):
        frappe.db.set_value("Global Defaults", "Global Defaults", "default_company", company)
        frappe.db.set_default("company", company)
    return company


# ---------------------------------------------------------------------------
# Data migration
# ---------------------------------------------------------------------------

# Legacy records remain as the immutable migration source. Never infer identity
# from a display name: explicit markers also cover tasks without issue keys.
def migrate(dry_run=True):
    """Validate/migrate legacy records; default rolls back all data changes.

    Run ensure_custom_fields (bench migrate) separately: schema DDL can commit
    implicitly, so it must never be mixed with this transactional data migration.
    """
    dry_run = str(dry_run).lower() not in ("false", "0")
    for dt, field in (("Project", "pulse_legacy_project"), ("Task", "pulse_legacy_task")):
        if not frappe.db.has_column(dt, field):
            frappe.throw("Run bench migrate to install Pulse migration identity fields first.")
    flags = ("mute_emails", "mute_messages", "in_import", "pulse_migration")
    previous = {key: frappe.flags.get(key) for key in flags}
    present = {key: key in frappe.flags for key in flags}
    frappe.db.savepoint("pulse_legacy_migration")
    try:
        for key in flags:
            frappe.flags[key] = True
        _migrate_issue_types()
        projects = _migrate_projects()
        tasks = _migrate_tasks(projects)
        _repoint_retained(projects, tasks)
        _migrate_assignments(tasks)
        _validate_migration(projects, tasks)
        result = {"projects": projects, "tasks": tasks, "dry_run": dry_run}
        if dry_run:
            frappe.db.rollback(save_point="pulse_legacy_migration")
        else:
            frappe.db.commit()
        return result
    except Exception as original_error:
        try:
            frappe.db.rollback(save_point="pulse_legacy_migration")
        except Exception:
            # Deadlocks can make MariaDB roll back the transaction itself,
            # invalidating its savepoints. Preserve the original failure and
            # reset the connection transaction rather than retrying migration.
            try:
                frappe.db.rollback()
            except Exception as rollback_error:
                if hasattr(original_error, "add_note"):
                    original_error.add_note(f"Full migration rollback also failed: {rollback_error}")
        raise
    finally:
        for key in flags:
            if present[key]:
                frappe.flags[key] = previous[key]
            else:
                frappe.flags.pop(key, None)


def _default_company():
    return (frappe.db.get_single_value("Global Defaults", "default_company")
            or frappe.db.get_value("Company", {}, "name"))


def _legacy_names(doctype):
    if not frappe.db.exists("DocType", doctype):
        return []
    return frappe.get_all(doctype, pluck="name", order_by="creation asc")


def _copy_fields(source, target, fields):
    for source_field, target_field in fields:
        value = source.get(source_field)
        if value is not None and target.meta.has_field(target_field):
            target.set(target_field, value)


def _copy_children(source, target, fields):
    for field in fields:
        if target.meta.has_field(field):
            child_meta = frappe.get_meta(target.meta.get_field(field).options)
            allowed = {df.fieldname for df in child_meta.fields}
            for row in source.get(field) or []:
                target.append(field, {k: v for k, v in row.items() if k in allowed})


def _migrate_projects():
    mapping = {}
    for name in _legacy_names("Pulse Project"):
        existing = frappe.db.get_value("Project", {"pulse_legacy_project": name}, "name")
        if existing:
            mapping[name] = existing
            continue
        source = frappe.get_doc("Pulse Project", name).as_dict()
        # An old migration without markers needs an operator-reviewed mapping.
        if frappe.db.exists("Project", {"project_name": source.get("project_name") or name}):
            frappe.throw(f"Project {name}: matching native project has no migration marker; review and set pulse_legacy_project before retrying.")
        doc = frappe.new_doc("Project")
        doc.pulse_legacy_project = name
        doc.project_name = source.get("project_name") or name
        _copy_fields(source, doc, [(f, f) for f in (
            "status", "holiday_list", "expected_start_date", "expected_end_date",
            "pulse_project_key", "pulse_enable_scrum", "pulse_board_type",
            "pulse_default_sprint_length", "task_counter", "pulse_is_template")]
            + [("description", "notes")])
        if doc.meta.has_field("company"):
            doc.company = source.get("company") or _default_company()
        _copy_children(source, doc, ("users", "pulse_task_statuses", "pulse_task_types"))
        doc.insert(ignore_permissions=True)
        mapping[name] = doc.name
    return mapping


def _migrate_issue_types():
    for name in _legacy_names("Pulse Issue Type"):
        if not frappe.db.exists("Task Type", name):
            frappe.get_doc({"doctype": "Task Type", "__newname": name,
                            "name": name}).insert(ignore_permissions=True)


def _mapped(value, mapping, doctype):
    if not value:
        return None
    if value in mapping:
        return mapping[value]
    if frappe.db.exists(doctype, value):
        return value
    frappe.throw(f"Unresolved legacy {doctype} reference: {value}")


def _migrate_tasks(project_map):
    mapping, sources = {}, {}
    for name in _legacy_names("Pulse Task"):
        source = sources[name] = frappe.get_doc("Pulse Task", name).as_dict()
        existing = frappe.db.get_value("Task", {"pulse_legacy_task": name}, "name")
        if existing:
            mapping[name] = existing
            continue
        if source.get("issue_key") and frappe.db.exists("Task", {"issue_key": source["issue_key"]}):
            frappe.throw(f"Task {name}: issue key already exists without migration marker; review and set pulse_legacy_task before retrying.")
        doc = frappe.new_doc("Task")
        doc.pulse_legacy_task = name
        doc.subject = source.get("subject") or name
        doc.project = _mapped(source.get("project"), project_map, "Project")
        _copy_fields(source, doc, [(f, f) for f in (
            "status", "priority", "description", "exp_start_date", "exp_end_date",
            "expected_time", "is_milestone", "is_group", "progress", "issue_key", "seq",
            "pulse_sprint", "pulse_rank", "pulse_release", "pulse_story_points",
            "pulse_archived", "pulse_recurring", "workflow_state")]
            + [("task_type", "type"), ("actual_start_date", "act_start_date"),
               ("actual_end_date", "act_end_date")])
        _copy_children(source, doc, ("pulse_labels",))
        doc.insert(ignore_permissions=True)
        mapping[name] = doc.name
    # Legacy tasks allowed children without an is_group flag. ERPNext requires
    # every parent to be a group before attaching any child.
    for parent in {source.get("parent_task") for source in sources.values()} - {None, ""}:
        parent_name = _mapped(parent, mapping, "Task")
        parent_doc = frappe.get_doc("Task", parent_name)
        if not parent_doc.is_group:
            parent_doc.is_group = 1
            parent_doc.save(ignore_permissions=True)
    # Complete mappings first, including on a retry of a partially migrated site.
    for name, source in sources.items():
        doc = frappe.get_doc("Task", mapping[name])
        changed = False
        for field in ("parent_task", "pulse_epic"):
            if source.get(field):
                value = _mapped(source[field], mapping, "Task")
                if doc.get(field) != value:
                    doc.set(field, value)
                    changed = True
        # ERPNext's native dependency child table (when used by legacy Tasks).
        for row in source.get("depends_on") or []:
            task = _mapped(row.get("task"), mapping, "Task")
            if task and not any(r.task == task for r in doc.get("depends_on") or []):
                doc.append("depends_on", {"task": task})
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
    return mapping


def _retained_filters(dt, filters):
    filters = dict(filters)
    if frappe.get_meta(dt).istable:
        filters["parenttype"] = ["not in", ["Pulse Project", "Pulse Task"]]
    return filters


def _retained_link_fields():
    """Discover native and Pulse Link fields, including custom/child doctypes."""
    fields = {}
    for dt in frappe.get_all("DocType", pluck="name"):
        if dt in ("Pulse Project", "Pulse Task") or frappe.get_meta(dt).issingle or frappe.get_meta(dt).is_virtual:
            continue
        for df in frappe.get_meta(dt).fields:
            if df.fieldtype == "Link" and df.options in ("Project", "Task", "Pulse Project", "Pulse Task"):
                # Legacy child rows stay attached to their untouched source docs.
                fields[(dt, df.fieldname)] = df.options.replace("Pulse ", "")
    return fields


def _repoint_retained(project_map, task_map):
    maps = {"Project": project_map, "Task": task_map}
    for (dt, field), kind in _retained_link_fields().items():
        for old, new in maps[kind].items():
            if old == new:
                continue
            for row in frappe.get_all(dt, filters=_retained_filters(dt, {field: old}), fields=["name"]):
                frappe.db.set_value(dt, row.name, field, new, update_modified=False)
    # Some core typed references (File and Version) are stored as Data fields,
    # so Dynamic Link metadata alone cannot discover all attached records.
    for dt, type_field, name_field in _retained_dynamic_fields():
        for kind, mapping in maps.items():
            for old, new in mapping.items():
                filters = _retained_filters(dt, {type_field: "Pulse " + kind, name_field: old})
                for row in frappe.get_all(dt, filters=filters, pluck="name"):
                    frappe.db.set_value(dt, row, {type_field: kind, name_field: new}, update_modified=False)


def _retained_dynamic_fields():
    pairs = set()
    for dt in frappe.get_all("DocType", pluck="name"):
        meta = frappe.get_meta(dt)
        if meta.issingle or meta.is_virtual or dt in ("Pulse Project", "Pulse Task"):
            continue
        for df in meta.fields:
            if df.fieldtype == "Dynamic Link":
                pairs.add((dt, df.options, df.fieldname))
    for dt, type_field, name_field in (
        ("File", "attached_to_doctype", "attached_to_name"),
        ("Version", "ref_doctype", "docname"),
    ):
        if frappe.db.has_column(dt, type_field) and frappe.db.has_column(dt, name_field):
            pairs.add((dt, type_field, name_field))
    return sorted(pairs)


def _migrate_assignments(task_map):
    import json
    for old, new in task_map.items():
        raw = frappe.db.get_value("Pulse Task", old, "_assign")
        users = json.loads(raw) if raw else []
        for user in users:
            if not frappe.db.exists("User", user):
                frappe.throw(f"Legacy assignment on {old} references missing user {user}")
            filters = {"reference_type": "Task", "reference_name": new,
                       "allocated_to": user, "status": "Open"}
            if not frappe.db.exists("ToDo", filters):
                frappe.get_doc({"doctype": "ToDo", **filters,
                                "description": f"Migrated assignment from {old}"}).insert(ignore_permissions=True)
        assigned = frappe.get_all("ToDo", filters={"reference_type": "Task", "reference_name": new,
                                                   "status": "Open"}, pluck="allocated_to")
        frappe.db.set_value("Task", new, "_assign", json.dumps(sorted(set(filter(None, assigned)))), update_modified=False)


def _validate_migration(project_map, task_map):
    # Use exactly the same typed-reference coverage for mutation and validation.
    for dt, type_field, name_field in _retained_dynamic_fields():
        for kind, mapping in (("Project", project_map), ("Task", task_map)):
            for old in mapping:
                filters = _retained_filters(dt, {type_field: "Pulse " + kind, name_field: old})
                if frappe.db.exists(dt, filters):
                    frappe.throw(f"Unmigrated dynamic reference: {dt}.{name_field} -> {old}")
    for kind, mapping, marker in (("Project", project_map, "pulse_legacy_project"),
                                   ("Task", task_map, "pulse_legacy_task")):
        if len(set(mapping.values())) != len(mapping):
            frappe.throw(f"Multiple legacy {kind} records map to the same native record")
        for old, new in mapping.items():
            if frappe.db.get_value(kind, new, marker) != old:
                frappe.throw(f"Migration identity mismatch for {kind} {old}")
    for (dt, field), kind in _retained_link_fields().items():
        mapping = project_map if kind == "Project" else task_map
        for old, new in mapping.items():
            if old != new and frappe.db.exists(dt, _retained_filters(dt, {field: old})):
                frappe.throw(f"Unmigrated reference remains: {dt}.{field} -> {old}")


def smoke():
    """Quick health check of the consolidated app's endpoints."""
    frappe.set_user("Administrator")
    results = []

    def t(label, fn):
        try:
            fn()
            results.append(("OK", label))
        except Exception as e:
            results.append(("FAIL", f"{label}: {type(e).__name__} {str(e)[:90]}"))

    for dt in ["Pulse Objective", "Pulse Risk", "Pulse Meeting", "Pulse Portfolio",
               "Pulse Retrospective", "Pulse Document", "Pulse Timesheet", "Pulse Sprint"]:
        t(f"list {dt}", lambda dt=dt: frappe.get_all(dt, limit=1))

    from pulse.api.spa import get_board, get_task
    from pulse.api.analytics import get_analytics
    from pulse.api.audit import get_audit_log
    from pulse.api.dashboards import get_my_dashboard, get_dashboard_stats

    t("get_board", lambda: get_board())
    t("get_analytics", lambda: get_analytics())
    t("get_audit_log", lambda: get_audit_log(limit=5))
    t("get_dashboard_stats", lambda: get_dashboard_stats())
    t("get_my_dashboard", lambda: get_my_dashboard())
    tasks = frappe.get_all("Task", filters={"issue_key": ["is", "set"]}, pluck="name")
    if tasks:
        t("get_task drawer", lambda: get_task(tasks[0]))

    def as_junior():
        frappe.set_user("erin@pulse.demo")
        try:
            get_board()
        finally:
            frappe.set_user("Administrator")
    t("get_board as junior (perm path)", as_junior)

    okc = sum(1 for r in results if r[0] == "OK")
    print("SMOKE_OK", okc, "/", len(results))
    for st, label in results:
        if st == "FAIL":
            print("  FAIL", label)
    return results
