# Pulse automation and MCP operations

Pulse uses native ERPNext Project/Task/ToDo records. The bounded dispatcher is
`pulse.api.automation.execute(operation, values)`. It preserves the current user's
permissions, field permissions, configured stage requirements and approval rules.
Call `describe_operations` with `{}` for current required/optional input names.
Use native record IDs, not display titles. Inputs are ordinary JSON objects.

Quest Automations provides each operation below with a `pulse_` prefix in the
ERPNext action picker. The builder also has 19 Pulse/document-event presets,
including task completion, assignment, mentions, reminders, module membership,
page/request/approval updates, delivery handoffs, order submission and CRM updates.
These reuse the existing generic document-event trigger; no duplicate scheduler
or webhook registration is needed. Completion filters distinguish a transition
from a later edit to an already completed task. Due/overdue events originate from
the scheduled Pulse inbox notification; they are not proof that email was sent.

| Operation | Required values |
| --- | --- |
| `create_project` | `project_name` |
| `create_task` | `project`, `subject` |
| `get_task` | `task` |
| `update_task` | `task`, `fields` |
| `set_status` | `task`, `state` |
| `assign_task` | `task`, `user` |
| `unassign_task` | `task`, `user` |
| `add_comment` | `task`, `text` |
| `add_dependency` | `task`, `depends_on` |
| `create_module` | `project`, `title` |
| `find_tasks` | None |
| `get_project` | `project` |
| `update_project` | `project`, `fields` |
| `archive_task` | `task` |
| `restore_task` | `task` |
| `add_subtask` | `parent`, `subject` |
| `remove_dependency` | `name` |
| `add_checklist_item` | `task`, `item` |
| `set_checklist_item` | `name`, `is_done` |
| `bulk_update_tasks` | `tasks`, `fields` |
| `list_modules` | `project` |
| `get_module` | `name` |
| `update_module` | `name`, `fields` |
| `add_module_tasks` | `name`, `tasks` |
| `remove_module_tasks` | `name`, `tasks` |
| `list_pages` | None |
| `get_page` | `name` |
| `create_page` | `project`, `title` |
| `update_page` | `name`, `modified`, `fields` |
| `add_page_comment` | `name`, `content` |
| `list_requests` | None |
| `get_request` | `name` |
| `create_request` | `project`, `title` |
| `review_request` | `name`, `status` |
| `accept_request` | `name` |
| `clone_project_template` | `template`, `project_name` |
| `get_project_team` | `project` |
| `add_project_member` | `project`, `user` |
| `remove_project_member` | `project`, `user` |
| `transfer_project_owner` | `project`, `user` |
| `invite_project_member` | `project`, `email`, `first_name` |
| `preview_offboarding` | `user`, `replacement` |
| `offboard_user` | `user`, `replacement`, `preview_token` |
| `create_delivery_handoff` | `source_doctype`, `source_name`, `project_name` |
| `get_delivery_handoff` | `source_doctype`, `source_name` |
| `share_task_external` | `task`, `user` |
| `revoke_task_external` | `task`, `user` |
| `reply_external` | `task`, `content` |
| `get_task_fields` | `task` |
| `update_task_fields` | `task`, `fields` |
| `get_project_field_config` | `project` |
| `save_project_field_config` | `project`, `rules` |
| `create_custom_task_field` | `project`, `label` |
| `get_task_approvals` | `task` |
| `request_task_approval` | `task`, `reviewer` |
| `decide_task_approval` | `name`, `decision` |
| `preview_task_import` | `project`, `content` |
| `import_tasks` | `project`, `content` |
| `export_tasks` | `project` |
| `describe_operations` | None |
| `get_task_creation_fields` | `project` |

The `fields` object updates only permitted fields. Task creation accepts optional `field_values` for configured writable custom fields; use `get_task_creation_fields` to inspect the creation form. `rules` configures project field
requirements; `approval_statuses` is an optional list of stage names. Page updates
require the last read `modified` value; initialized collaborative bodies are edited
through the page editor rather than overwritten by automation. Import uses bounded
CSV and stable batch identities. Handoffs use stable source IDs and reuse existing
native Sales Order project links. Schema creation, invitations and offboarding
retain their stricter administrator checks. Offboarding requires the preview token
from `preview_offboarding`, and a stale plan is rejected.

## Triggers, privacy and reliability

Native events capture the original values and previous snapshot. Each workflow's
publishing user must still read the source; field permissions and masks filter both
snapshots before they enter a run. Event identity includes record, modified timestamp,
event and trigger. A repeated delivery returns the same run. Workflow ancestry is
internal metadata, separate from webhook input: a workflow cannot repeat within one
chain, and chains stop after 16 workflows. Rejected triggers are logged. Independent
later events remain valid. Module addition/removal also emits a durable scoped
`Pulse Activity Log` event of type `Module Membership Changed`.

Publishing snapshots a workflow and its run-as user. Workers require that user to
remain enabled and a System Manager. Completed outputs/checkpoints are persisted;
failed/uncertain actions remain visible in execution history. Preview resolves
inputs without native writes or external calls. There is no automatic replay of an
uncertain create: inspect the destination before intentionally starting another run.
A distinct manual run is a distinct operation and may create additional work.

## CRM/order example

Choose Sales order submitted (or CRM deal updated with a stage filter), then add
`pulse_create_delivery_handoff` with source_doctype, source_name from trigger.name,
and project_name. An optional template copies native tasks, hierarchy, labels,
checklists and permitted configured field values. Repeated handoff of the same
source returns its existing project. Map the returned project into later task steps.

## MCP deployment

The standalone `mcp/pulse_mcp_server.py` provides `pulse_work`. The existing ERPNext
connection can discover the same tool through Quest Media Tools' `assistant_tools`
hook when FAC custom_tools is enabled. Its schema resolves the installed Pulse
catalog, so operations stay synchronized. Deploy/migrate matching Pulse, Quest
Automations and Quest Media Tools versions, refresh server discovery, and reconnect
the client to load the changed tool schema. Existing credentials and permissions
remain authoritative. Local tests do not establish production tool availability.

Validation for this release: 57 Quest unit tests cover action/catalog parity, current
builder graph validation, dry-run isolation, trigger presets, event privacy, callback
boundaries and loop guards. Three real QA worker tests cover native task creation,
duplicate events, self-trigger rejection and failed-run visibility. See the current
company-readiness validation log for browser and deployment status.
