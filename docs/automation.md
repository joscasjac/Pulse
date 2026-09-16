# ERPNext MCP and Quest Automations

The standalone server remains in `mcp/pulse_mcp_server.py`. Sites using Frappe
Assistant Core can instead discover `pulse_work` through Quest Media Tools' `assistant_tools`
hook. Enable FAC's custom_tools plugin, deploy/migrate Pulse and Quest Media Tools, refresh server tool
discovery and reconnect the client. This extends the existing ERPNext credentials
and session permissions; it does not create a second account or bypass access.

The bounded API is `pulse.api.automation.execute(operation, values)`. Operations:
create_project, create_task, get_task, update_task, set_status, assign_task,
unassign_task, add_comment, add_dependency, create_module. Use native record IDs.
`create_task` takes project and subject, with optional description, assignees,
priority, state, type (`task_type`), dates (`exp_start_date`, `exp_end_date`),
expected_time, pulse_story_points, pulse_labels, parent_task and module.
`update_task` takes task and a fields object; status uses set_status.

Quest Automations exposes the same operations with the `pulse_` prefix in its
ERPNext action selector and catalog. Map previous-step output `name` into later
actions to create a project followed by tasks. Deploy the matching Quest update
alongside Pulse; missing Pulse produces an explicit action error. Draft preview
does not perform actions. Automation runs can trigger task emails and realtime
updates. After an uncertain create, inspect the destination before retrying;
creation is not idempotent across separately started runs.

Implementation is local pending deployment. The user's existing ERPNext MCP was
verified read-only against native Task metadata. New tool discovery and end-to-end
execution through the deployed connector have not yet been verified.
