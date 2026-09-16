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

ALLOWED = {
    "create_project": {"project_name", "company", "customer", "sales_order", "expected_start_date", "expected_end_date", "pulse_project_key"},
    "create_task": {"project", "subject", "state", "task_type", "priority", "description", "assignees", "exp_start_date", "exp_end_date", "parent_task", "expected_time", "pulse_story_points", "pulse_labels", "module"},
    "create_module": {"project", "title", "description", "status", "start_date", "due_date", "lead"},
}


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
    from pulse.api import spa, modules
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
    return handlers[operation](**values)
