"""Bounded automation operations shared by MCP and Quest Automations."""
import frappe

OPERATIONS = {
    "create_project": ("project_name",),
    "create_task": ("project", "subject"),
    "get_task": ("task",),
    "update_task": ("task", "fields"),
    "set_status": ("task", "state"),
    "assign_task": ("task", "user"),
    "unassign_task": ("task", "user"),
    "add_comment": ("task", "text"),
    "add_dependency": ("task", "depends_on"),
    "create_module": ("project", "title"),
}

OPERATIONS.update({'find_tasks': (),
 'get_project': ('project',),
 'update_project': ('project', 'fields'),
 'archive_task': ('task',),
 'restore_task': ('task',),
 'add_subtask': ('parent', 'subject'),
 'remove_dependency': ('name',),
 'add_checklist_item': ('task', 'item'),
 'set_checklist_item': ('name', 'is_done'),
 'bulk_update_tasks': ('tasks', 'fields'),
 'list_modules': ('project',),
 'get_module': ('name',),
 'update_module': ('name', 'fields'),
 'add_module_tasks': ('name', 'tasks'),
 'remove_module_tasks': ('name', 'tasks'),
 'list_pages': (),
 'get_page': ('name',),
 'create_page': ('project', 'title'),
 'update_page': ('name', 'modified', 'fields'),
 'add_page_comment': ('name', 'content'),
 'list_requests': (),
 'get_request': ('name',),
 'create_request': ('project', 'title'),
 'review_request': ('name', 'status'),
 'accept_request': ('name',),
 'clone_project_template': ('template', 'project_name')})

OPERATIONS.update({"get_project_team": ("project",), "add_project_member": ("project", "user"),
                   "remove_project_member": ("project", "user"), "transfer_project_owner": ("project", "user")})

OPERATIONS.update({'invite_project_member': ('project', 'email', 'first_name'), 'preview_offboarding': ('user', 'replacement'), 'offboard_user': ('user', 'replacement', 'preview_token'), 'create_delivery_handoff': ('source_doctype', 'source_name', 'project_name'), 'get_delivery_handoff': ('source_doctype', 'source_name'), 'share_task_external': ('task', 'user'), 'revoke_task_external': ('task', 'user'), 'reply_external': ('task', 'content'), 'get_task_fields': ('task',), 'update_task_fields': ('task', 'fields'), 'get_project_field_config': ('project',), 'save_project_field_config': ('project', 'rules'), 'create_custom_task_field': ('project', 'label'), 'get_task_approvals': ('task',), 'request_task_approval': ('task', 'reviewer'), 'decide_task_approval': ('name', 'decision'), 'preview_task_import': ('project', 'content'), 'import_tasks': ('project', 'content'), 'export_tasks': ('project',)})

OPERATIONS["describe_operations"] = ()
OPERATIONS["get_task_creation_fields"] = ("project",)

ALLOWED = {
    "create_project": {"project_name", "company", "customer", "sales_order", "expected_start_date", "expected_end_date", "pulse_project_key"},
    "create_task": {"project", "subject", "state", "task_type", "priority", "description", "assignees", "exp_start_date", "exp_end_date", "parent_task", "expected_time", "pulse_story_points", "pulse_labels", "module", "field_values"},
    "create_module": {"project", "title", "description", "status", "start_date", "due_date", "lead"},
}

ALLOWED.update({
    "remove_project_member": {"project", "user", "replacement"},
    "find_tasks": {"q", "project", "exclude", "limit"},
    "bulk_update_tasks": {"tasks", "fields", "assign", "unassign"},
    "list_pages": {"project", "query"},
    "create_page": {"project", "title", "content", "tasks", "template"},
    "list_requests": {"project", "status"},
    "create_request": {"project", "title", "description", "reviewer"},
    "review_request": {"name", "status", "reviewer", "duplicate_of", "note"},
    "accept_request": {"name", "reviewer", "note"},
    "clone_project_template": {"template", "project_name", "customer", "sales_order"},
})

ALLOWED.update({'invite_project_member': {'first_name', 'last_name', 'project', 'email'}, 'create_delivery_handoff': {'source_name', 'source_doctype', 'template', 'project_name'}, 'save_project_field_config': {'rules', 'approval_statuses', 'project'}, 'create_custom_task_field': {'fieldtype', 'label', 'options', 'project'}, 'decide_task_approval': {'name', 'decision', 'note'}})


def _update_fields(values, allowed):
    fields = values["fields"]
    if not isinstance(fields, dict) or not fields or set(fields) - allowed:
        frappe.throw("Provide supported fields to update")
    return fields


@frappe.whitelist(methods=["POST"])
def execute(operation, values=None):
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to manage Pulse work.", frappe.PermissionError)
    if operation not in OPERATIONS:
        frappe.throw("Unsupported Pulse operation")
    if isinstance(values, str):
        values = frappe.parse_json(values)
    if not isinstance(values, dict):
        frappe.throw("Provide an object of action values")
    required = OPERATIONS[operation]
    if any(values.get(key) in (None, "") for key in required):
        frappe.throw("Required fields: " + ", ".join(required))
    if set(values) - ALLOWED.get(operation, set(required)):
        frappe.throw("Unsupported action fields")
    if operation == "describe_operations":
        return {key: {"required": list(required), "optional": sorted(ALLOWED.get(key, set(required)) - set(required))}
                for key, required in OPERATIONS.items()}
    from pulse.api import spa, modules, tasks, documents, intake, business, team, handoffs, external, task_config, approvals, transfer
    handlers = {
        "invite_project_member": team.invite_member, "preview_offboarding": team.preview_offboarding,
        "offboard_user": team.offboard_user, "create_delivery_handoff": handoffs.create,
        "get_delivery_handoff": handoffs.existing, "share_task_external": external.share,
        "revoke_task_external": external.revoke, "reply_external": external.reply,
        "get_task_fields": task_config.get_task_fields,
        "get_task_creation_fields": task_config.get_creation_fields,
        "update_task_fields": lambda task, fields: task_config.update_task_fields(task, fields),
        "get_project_field_config": task_config.get_field_config,
        "save_project_field_config": task_config.save_field_config,
        "create_custom_task_field": task_config.create_custom_task_field,
        "get_task_approvals": approvals.get_approvals, "request_task_approval": approvals.request_approval,
        "decide_task_approval": approvals.decide, "preview_task_import": transfer.preview_import,
        "import_tasks": transfer.import_tasks, "export_tasks": transfer.export_tasks,
    }
    if operation in handlers:
        return handlers[operation](**values)
    team_actions = {"get_project_team": team.get_team, "add_project_member": team.add_member,
                    "remove_project_member": team.remove_member, "transfer_project_owner": team.transfer_owner}
    if operation in team_actions:
        return team_actions[operation](**values)
    from pulse.hooks.permissions import require_permission
    if operation == "get_project":
        doc = require_permission("Project", values["project"])
        doc.apply_fieldlevel_read_permissions()
        return doc.as_dict()
    if operation == "update_project":
        fields = _update_fields(values, ALLOWED["create_project"] | {"status"})
        doc = require_permission("Project", values["project"], "write")
        doc.update(fields)
        doc.save()
        doc.apply_fieldlevel_read_permissions()
        return doc.as_dict()
    if operation in ("archive_task", "restore_task"):
        return tasks.bulk_update([values["task"]], {"pulse_archived": int(operation == "archive_task")})
    if operation == "update_module":
        fields = _update_fields(values, ALLOWED["create_module"] - {"project"})
        doc = require_permission("Pulse Module", values["name"], "write")
        payload = {key: doc.get(key) for key in ALLOWED["create_module"]}
        return modules.save_module(name=doc.name, **{**payload, **fields})
    if operation in ("add_module_tasks", "remove_module_tasks"):
        return modules.set_tasks(values["name"], values["tasks"], remove=int(operation == "remove_module_tasks"))
    if operation == "update_page":
        fields = _update_fields(values, {"title", "content", "tasks"})
        doc = require_permission("Pulse Document", values["name"], "write")
        if "content" in fields and doc.get("collab_updates"):
            frappe.throw("Edit collaborative page content in the page editor; automation can update its title and task links.")
        return documents.save_page(project=doc.project, name=doc.name, modified=values["modified"],
            title=fields.get("title", doc.title), content=fields.get("content", doc.content), tasks=fields.get("tasks"))
    if operation == "create_project":
        return spa.save_entity({"doctype": "Project", **values})
    if operation == "create_module":
        return modules.save_module(**values)
    if operation == "update_task":
        if not isinstance(values["fields"], dict):
            frappe.throw("fields must be an object")
        return spa.update_task(values["task"], **values["fields"])
    handlers = {"create_task": spa.create_task, "get_task": spa.get_task,
        "set_status": spa.update_task_state, "assign_task": spa.assign_task,
        "unassign_task": spa.unassign_task, "add_comment": spa.add_comment,
        "add_dependency": spa.add_dependency}
    handlers.update({
        "find_tasks": spa.search_tasks, "add_subtask": spa.add_subtask,
        "remove_dependency": spa.remove_dependency, "add_checklist_item": spa.add_checklist_item,
        "set_checklist_item": spa.toggle_checklist_item, "bulk_update_tasks": tasks.bulk_update,
        "list_modules": modules.list_modules, "get_module": modules.get_module,
        "list_pages": documents.list_pages, "get_page": documents.get_page,
        "create_page": documents.save_page, "add_page_comment": documents.add_comment,
        "list_requests": intake.list_requests, "get_request": intake.get_request,
        "create_request": intake.create_request, "review_request": intake.review_request,
        "accept_request": intake.accept_request, "clone_project_template": business.clone_template,
    })
    return handlers[operation](**values)
