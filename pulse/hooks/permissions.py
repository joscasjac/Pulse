"""Shared row visibility for native ERPNext records and their Pulse children.

Query hooks constrain lists; document hooks constrain direct API reads/writes.
Hooks only veto: Frappe's native role and user permissions still apply.
"""
import json
import frappe


def require_permission(doctype, name, permission_type="read"):
    doc = frappe.get_doc(doctype, name)
    doc.check_permission(permission_type)
    return doc


class TaskReadScopeMixin:
    """Apply linked-record visibility at Frappe's native document read boundary."""

    def apply_fieldlevel_read_permissions(self):
        super().apply_fieldlevel_read_permissions()
        self.set("depends_on", [row for row in self.get("depends_on") or []
            if row.get("task") and frappe.has_permission("Task", "read", doc=row.task)])
        self.depends_on_tasks = ",".join(row.task for row in self.get("depends_on") or [])
        if self.get("parent_task") and not frappe.has_permission("Task", "read", doc=self.parent_task):
            self.parent_task = None


def preserve_private_task_links(doc, method=None):
    """A client roundtrip must not delete relationships omitted from its read.

    Restore only pre-existing invisible links before native Task validation.
    Readable links remain editable, and validate_scope still rejects new links
    to unreadable targets. No persistence occurs outside the normal save.
    """
    if doc.is_new() or doc.flags.ignore_permissions or _admin(frappe.session.user):
        return
    before = doc.get_doc_before_save()
    if not before:
        return
    private_rows = [row for row in before.get("depends_on") or []
        if row.get("task") and not frappe.has_permission("Task", "read", doc=row.task)]
    if private_rows:
        private_names = {row.name for row in private_rows}
        private_targets = {row.task for row in private_rows}
        doc.set("depends_on", [row for row in doc.get("depends_on") or []
            if row.name not in private_names and row.task not in private_targets])
        for row in private_rows:
            doc.append("depends_on", row.as_dict())
    if (before.get("parent_task") and not doc.get("parent_task")
            and not frappe.has_permission("Task", "read", doc=before.parent_task)):
        doc.parent_task = before.parent_task


def _admin(user):
    return user == "Administrator" or bool(set(frappe.get_roles(user)) & {"Pulse Admin", "System Manager"})


def _allowed_projects(user):
    # Do not cache across writes: membership can change during the request.
    return frappe.get_all("Project User", filters={"user": user, "parenttype": "Project"}, pluck="parent")


def _project_sql(user, field):
    u = frappe.db.escape(user)
    return (f"{field} IN (SELECT p.name FROM `tabProject` p WHERE p.owner = {u} "
            f"OR EXISTS (SELECT 1 FROM `tabProject User` pu WHERE pu.parent = p.name "
            f"AND pu.parenttype = 'Project' AND pu.user = {u}))")


def project_query_conditions(user=None):
    user = user or frappe.session.user
    return "" if _admin(user) else _project_sql(user, "`tabProject`.`name`")


def task_query_conditions(user=None):
    user = user or frappe.session.user
    if _admin(user):
        return ""
    u = frappe.db.escape(user)
    conditions = ["(" + _project_sql(user, "`tabTask`.`project`") +
                  f" OR (COALESCE(`tabTask`.`project`, '') = '' AND `tabTask`.`owner` = {u}))"]
    if _top_pulse_role(user) in ("Pulse Junior Developer", "Pulse Intern"):
        assigned = frappe.db.escape(json.dumps(user))
        conditions.append(f"(`tabTask`.`owner` = {u} OR JSON_CONTAINS(COALESCE(NULLIF(`tabTask`.`_assign`, ''), '[]'), {assigned}))")
    return " AND ".join(conditions)


def project_has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    if _admin(user) or doc.owner == user or doc.name in _allowed_projects(user):
        return True
    return False


def task_has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    if _admin(user):
        return True
    project = doc.get("project")
    if project:
        if project not in _allowed_projects(user) and frappe.db.get_value("Project", project, "owner") != user:
            return False
    elif doc.owner != user:
        return False
    if _top_pulse_role(user) in ("Pulse Junior Developer", "Pulse Intern"):
        if doc.owner != user and user not in (frappe.parse_json(doc.get("_assign") or "[]") or []):
            return False
    return True


# Records tied to a task inherit its stricter visibility (including juniors).
TASK_LINKS = {"Pulse Checklist": "task", "Pulse Comment": "task",
              "Pulse Task Status Log": "task", "Pulse Dependency": "source_task"}
PROJECT_TYPES = ("Pulse Sprint", "Pulse Activity Log", "Pulse Recurring Task",
                 "Pulse Epic", "Pulse Release", "Pulse Document", "Pulse Risk",
                 "Pulse Meeting", "Pulse Objective")


def scoped_query_conditions(user=None, doctype=None):
    user = user or frappe.session.user
    if _admin(user):
        return ""
    if doctype == "Pulse Activity Log":
        task_scope = task_query_conditions(user)
        task_ref = ("EXISTS (SELECT 1 FROM `tabTask` WHERE " + task_scope +
                    " AND (`tabTask`.`name` = `tabPulse Activity Log`.`reference_name`"
                    " OR `tabTask`.`issue_key` = `tabPulse Activity Log`.`reference_name`))")
        return ("(" + _project_sql(user, "`tabPulse Activity Log`.`project`") +
                " AND (COALESCE(`tabPulse Activity Log`.`reference_doctype`, '') != 'Task' OR " + task_ref + "))")
    if doctype in TASK_LINKS:
        visible = frappe.get_list("Task", pluck="name", limit_page_length=0, user=user)
        names = ",".join(frappe.db.escape(name) for name in visible) or "NULL"
        fields = [TASK_LINKS[doctype]] + (["target_task"] if doctype == "Pulse Dependency" else [])
        return " AND ".join(f"`tab{doctype}`.`{field}` IN ({names})" for field in fields)
    return _project_sql(user, f"`tab{doctype}`.`project`")


def scoped_has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    if _admin(user):
        return True
    if doc.doctype == "Pulse Activity Log" and doc.get("reference_doctype") == "Task":
        ref = doc.get("reference_name")
        task = ref if frappe.db.exists("Task", ref) else frappe.db.get_value("Task", {"issue_key": ref}, "name")
        if not task or not frappe.has_permission("Task", "read", doc=task, user=user):
            return False
    if doc.doctype == "Pulse Dependency" and not frappe.has_permission(
            "Task", "read", doc=doc.get("target_task"), user=user):
        return False
    task_field = TASK_LINKS.get(doc.doctype)
    if task_field:
        task = doc.get(task_field)
        if not task or not frappe.has_permission("Task", "read", doc=task, user=user):
            return False
    else:
        project = doc.get("project")
        if not project or not frappe.has_permission("Project", "read", doc=project, user=user):
            return False
    return True


def sprint_query_conditions(user=None):
    return scoped_query_conditions(user, "Pulse Sprint")


def status_log_query_conditions(user=None):
    return scoped_query_conditions(user, "Pulse Task Status Log")


def _top_pulse_role(user):
    cache_key = f"_top_pulse_role:{user}"
    if hasattr(frappe.local, cache_key):
        return getattr(frappe.local, cache_key)
    pulse_roles = [
        "Pulse Admin",
        "Pulse Manager",
        "Pulse Team Lead",
        "Pulse Senior Developer",
        "Pulse Junior Developer",
        "Pulse Intern",
        "Pulse Viewer",
    ]
    user_roles = frappe.get_roles(user)
    for role in pulse_roles:
        if role in user_roles:
            setattr(frappe.local, cache_key, role)
            return role
    setattr(frappe.local, cache_key, None)
    return None


def on_todo_assign(doc, method=None):
    from pulse.hooks.events.assignment import enforce_hierarchy

    enforce_hierarchy(doc, method)


def validate_task_assignees(doc, method=None):
    before = doc.get_doc_before_save()
    old_assign = frappe.parse_json(before.get("_assign") or "[]") if before else []
    new_assign = frappe.parse_json(doc.get("_assign") or "[]")
    added = [u for u in new_assign if u not in old_assign]
    for user in added:
        from pulse.hooks.events.assignment import validate_assignment

        validate_assignment(frappe.session.user, user)




def pulse_activity_log_query(user=None):
    return scoped_query_conditions(user, 'Pulse Activity Log')


def pulse_allocation_query(user=None):
    return scoped_query_conditions(user, 'Pulse Allocation')




def pulse_risk_query(user=None):
    return scoped_query_conditions(user, 'Pulse Risk')


def pulse_goal_query(user=None):
    return scoped_query_conditions(user, 'Pulse Goal')


def pulse_document_query(user=None):
    return scoped_query_conditions(user, 'Pulse Document')


def pulse_sprint_query(user=None):
    return scoped_query_conditions(user, 'Pulse Sprint')


def pulse_recurring_task_query(user=None):
    return scoped_query_conditions(user, 'Pulse Recurring Task')


def pulse_change_request_query(user=None):
    return scoped_query_conditions(user, 'Pulse Change Request')


def pulse_retrospective_query(user=None):
    return scoped_query_conditions(user, 'Pulse Retrospective')


def pulse_decision_query(user=None):
    return scoped_query_conditions(user, 'Pulse Decision')


def pulse_meeting_query(user=None):
    return scoped_query_conditions(user, 'Pulse Meeting')


def pulse_dashboard_query(user=None):
    return scoped_query_conditions(user, 'Pulse Dashboard')


def pulse_checklist_query(user=None):
    return scoped_query_conditions(user, 'Pulse Checklist')


def pulse_comment_query(user=None):
    return scoped_query_conditions(user, 'Pulse Comment')


def pulse_task_status_log_query(user=None):
    return scoped_query_conditions(user, 'Pulse Task Status Log')


def pulse_dependency_query(user=None):
    return scoped_query_conditions(user, 'Pulse Dependency')


def timesheet_query_conditions(user=None):
    return _time_query(user, "Timesheet", "Timesheet Detail")


def legacy_timesheet_query_conditions(user=None):
    return _time_query(user, "Pulse Timesheet", "Pulse Timesheet Entry")


def _time_query(user, parent_type, child_type):
    user = user or frappe.session.user
    if _admin(user):
        return ""
    # Fetch through native permission-aware lists, including ERPNext User Permissions.
    tasks = frappe.get_list("Task", pluck="name", limit_page_length=0, user=user)
    projects = frappe.get_list("Project", pluck="name", limit_page_length=0, user=user)
    task_names = ",".join(frappe.db.escape(t) for t in tasks) or "NULL"
    project_names = ",".join(frappe.db.escape(p) for p in projects) or "NULL"
    condition = (f"NOT EXISTS (SELECT 1 FROM `tab{child_type}` td WHERE td.parent = `tab{parent_type}`.name "
                 f"AND td.parenttype = {frappe.db.escape(parent_type)} AND ((COALESCE(td.task, '') != '' AND "
                 + (f"td.task NOT IN ({task_names})" if tasks else "1=1") +
                 ") OR (COALESCE(td.project, '') != '' AND " +
                 (f"td.project NOT IN ({project_names})" if projects else "1=1") + ")))")
    if "Pulse Manager" not in frappe.get_roles(user):
        condition += f" AND `tab{parent_type}`.`user` = {frappe.db.escape(user)}"
    return condition


def timesheet_has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    if _admin(user):
        return True
    if "Pulse Manager" not in frappe.get_roles(user) and doc.get("user") != user:
        return False
    for row in (doc.get("time_logs") or doc.get("entries") or []):
        for field, doctype in (("task", "Task"), ("project", "Project")):
            if row.get(field) and not frappe.has_permission(doctype, "read", doc=row.get(field), user=user):
                return False
    return True


def validate_scope(doc, method=None):
    """Check linked targets as well as the original record when scope changes."""
    if doc.flags.get("ignore_permissions") or _admin(frappe.session.user):
        return
    if doc.doctype == "Task":
        if doc.get("project"):
            require_permission("Project", doc.project)
        before = doc.get_doc_before_save()
        previous_dependencies = {row.task for row in (before.get("depends_on") or [])} if before else set()
        for row in doc.get("depends_on") or []:
            if row.task and row.task not in previous_dependencies:
                require_permission("Task", row.task)
        for field, doctype in (("parent_task", "Task"), ("pulse_sprint", "Pulse Sprint")):
            if doc.get(field):
                require_permission(doctype, doc.get(field))
    elif doc.doctype in TASK_LINKS:
        # Comments are allowed to readers; modifying a checklist/dependency changes work.
        permission = "read" if doc.doctype == "Pulse Comment" else "write"
        if doc.get(TASK_LINKS[doc.doctype]):
            require_permission("Task", doc.get(TASK_LINKS[doc.doctype]), permission)
        if doc.doctype == "Pulse Dependency" and doc.get("target_task"):
            require_permission("Task", doc.target_task)
    elif doc.get("project"):
        require_permission("Project", doc.project)


def validate_timesheet(doc, method=None):
    if doc.flags.get("ignore_permissions"):
        return
    user = frappe.session.user
    manager = _admin(user) or "Pulse Manager" in frappe.get_roles(user)
    if not manager:
        before = doc.get_doc_before_save()
        if doc.get("user") != user or (before and before.get("user") != user):
            frappe.throw("You can only record your own time.", frappe.PermissionError)
    for row in doc.get("time_logs") or []:
        if row.get("task"):
            task = require_permission("Task", row.task)
            if row.get("project") != task.get("project"):
                frappe.throw("Time entry project must match its task.")
        if row.get("project"):
            project = require_permission("Project", row.project)
            if project.get("company") and project.company != doc.get("company"):
                frappe.throw("Time entry project must belong to the timesheet company.")


def freeze_legacy_timesheet(doc, method=None):
    if not doc.flags.get("ignore_permissions"):
        frappe.throw("Legacy Pulse timesheets are read-only. Record time using ERPNext Timesheet.", frappe.PermissionError)


def protect_task_time(doc, method=None):
    if (frappe.db.exists("Timesheet Detail", {"task": doc.name})
            or frappe.db.exists("Pulse Timesheet Entry", {"task": doc.name})):
        frappe.throw("This task has recorded time. Archive it instead of deleting its time history.")


def notification_query_conditions(user=None):
    user = user or frappe.session.user
    recipient = f"`tabPulse Notification`.`recipient` = {frappe.db.escape(user)}"
    from pulse.api.personal import reference_query
    return recipient + " AND " + reference_query("Pulse Notification", user)


def notification_has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    if doc.get("recipient") != user:
        return False
    from pulse.api.personal import _visible
    if not _visible(doc.get("reference_doctype"), doc.get("reference_name"), user):
        return False
    return True


def dashboard_query_conditions(user=None):
    user = user or frappe.session.user
    if _admin(user):
        return ""
    u = frappe.db.escape(user)
    return (f"(`tabPulse Dashboard`.`owner_user` = {u} OR (`tabPulse Dashboard`.`scope` != 'Personal' AND "
            "(COALESCE(`tabPulse Dashboard`.`project`, '') = '' OR " +
            _project_sql(user, "`tabPulse Dashboard`.`project`") + ")))")


def dashboard_has_permission(doc, user=None, permission_type=None, ptype=None):
    user = user or frappe.session.user
    if _admin(user):
        return True
    if doc.get("owner_user") == user:
        return True
    if doc.get("scope") == "Personal":
        return False
    if doc.get("project") and not frappe.has_permission("Project", "read", doc=doc.project, user=user):
        return False
    if (ptype or permission_type) not in (None, "read", "select") and "Pulse Manager" not in frappe.get_roles(user):
        return False
    return True


def pulse_label_query(user=None):
    return scoped_query_conditions(user, "Pulse Label")


PRIVATE_ATTACHMENT_TYPES = ("Task", "Pulse Document")


def validate_private_attachment(doc, method=None):
    """Prevent native File APIs from creating public or reparented Pulse leaks."""
    before = doc.get_doc_before_save()
    references = [(doc.get("attached_to_doctype"), doc.get("attached_to_name"))]
    if before:
        references.append((before.get("attached_to_doctype"), before.get("attached_to_name")))
    protected = [(dt, name) for dt, name in references if dt in PRIVATE_ATTACHMENT_TYPES and name]
    if not protected:
        return
    for doctype, name in set(protected):
        require_permission(doctype, name, "write")
    # Reject before core File.validate can move a private blob into public storage.
    if not int(doc.get("is_private") or 0) or (doc.get("file_url") or "").startswith("/files/"):
        frappe.throw("Task and document attachments must be private. Upload with is_private=1.", frappe.PermissionError)


def attachment_has_permission(doc, user=None, permission_type=None, ptype=None):
    doctype, name = doc.get("attached_to_doctype"), doc.get("attached_to_name")
    if doctype not in PRIVATE_ATTACHMENT_TYPES or not name:
        return True
    permission = "read" if (ptype or permission_type) in (None, "read", "select") else "write"
    if not frappe.has_permission(doctype, permission, doc=name, user=user or frappe.session.user):
        return False
    return True


def attachment_query_conditions(user=None):
    user = user or frappe.session.user
    conditions = []
    for doctype in PRIVATE_ATTACHMENT_TYPES:
        names = (frappe.get_list(doctype, pluck="name", limit_page_length=0, user=user)
                 if frappe.has_permission(doctype, "read", user=user) else [])
        visible = ",".join(frappe.db.escape(name) for name in names) or "NULL"
        conditions.append(f"(COALESCE(`tabFile`.`attached_to_doctype`, '') != {frappe.db.escape(doctype)} "
                          f"OR `tabFile`.`attached_to_name` IN ({visible}))")
    return " AND ".join(conditions)


class PrivateAttachmentDownloadMixin:
    """Native private-file serving calls this method without document hooks."""

    def is_downloadable(self):
        if attachment_has_permission(self, permission_type="read") is False:
            return False
        return super().is_downloadable()
