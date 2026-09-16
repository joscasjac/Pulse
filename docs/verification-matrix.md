# Pulse backlog verification matrix

## Release follow-up checkpoint

The user deferred mobile acceptance for the first release; the underlying mobile
backlog remains recorded below. Sprints, Intake and Timesheets are temporarily
hidden from navigation by request, not removed from the implementation.

Later focused evidence (supersedes the older snapshot only for these paths):

- Restricted-user Chrome checks passed for visible list/Kanban/detail and global
  search, hidden dependency omission, and denial of direct hidden project/task
  URLs. See browser-validation.md for the exact synthetic role and fixture scope.

- Native Task document reads: reproduced private dependency leakage and fixed
  Frappe client/REST v1 serialization through a Task class extension. Restricted
  read/save preserves private links while allowing visible-link removal.
  **127 integration cases passed**; the full command's unit phase had one stale
  hook-sequence expectation, corrected and passed in a focused rerun. See runtime
  evidence for exact logs and the remaining query/export/browser boundaries.

- Latest full suite: **125 integration tests pass; unit run reports 59 tests,
  OK with one skip**, exit 0 (`pulse-release-tests-read-scope.log`). Fixed a
  reproduced leak in generic Pulse Task reads: unreadable dependency child rows
  and derived IDs are excluded from responses without changing stored links.
  Readable dependencies remain returned. Generic native REST paths remain a
  separate boundary from this Pulse endpoint.

- Latest backend suite after native dependency permission parity: **124
  integration tests pass; unit run reports 59 tests, OK with one skip**, exit 0
  (`pulse-release-tests-permissions.log`). New native dependency targets now
  require read permission, matching the Pulse API; retained links do not block
  unrelated edits. Seven focused permission cases pass.

- Latest full backend rerun after dependency-hook/migration changes: **121
  integration tests passed; unit suite reported 59 tests, OK with one skip**,
  exit 0. Log: `../.work/pulse-bench/pulse-release-tests-dependencies-rerun.log`.
  A workload fixture was isolated from retained Administrator leave after the
  preceding run exposed that assumption; runtime behavior was correct.

- Current full local backend suite: **118 integration tests and 59 unit tests
  pass**, command exit 0 (`../.work/pulse-bench/pulse-release-tests.log`). An earlier
  run hit a timesheet fixture overlapping retained QA time; the fixture now picks
  a free interval without disabling ERPNext overlap validation. This run includes
  advance reminder inbox creation, read/unread behavior, permission filtering and
  deduplication, plus the automation API lifecycle. It is not production delivery
  or browser acceptance evidence.

- Frontend: 10 tests pass, including pending timeline move/resize rendering and
  rollback. The production build including CRM My work passed.
- Email: 4 queue tests pass; reminder integration 2 tests pass with actual native
  Notification Log insertion, retry deduplication and permission denial. Outbound
  sending was mocked. QA has no outgoing account. Read-only connected ERP checks
  confirm a default outgoing account, recent Sent queue records and email job
  executions; Pulse reminder registration and delivery remain pending. See
  [email reminders](email-reminders.md).
- Automation: 4 API unit tests and 1 native project/task/module lifecycle test pass
  (`automation-unit-tests.log`, `automation-integration-tests.log` in the local
  bench evidence directory). The lifecycle creates a project/module/task, assigns
  through ToDo, updates dates/hours, comments and completes the task; module
  progress reaches 100%. Fixtures are cleaned up.
- Quest Automations: 3 new action tests and editor build pass. Its full offline
  suite using system Python had one environment failure: missing `quickjs`.
- Quest Media Tools: new Pulse connector discovery/delegation test passes. The
  existing deployed ERPNext MCP was read successfully for native Task metadata;
  deployment and discovery of the new `pulse_work` tool are still pending.
  Its complete offline suite passes all 15 tests.
- CRM: six backend cases pass against official CRM v1.84.0 in a separate site,
  including real Sales User/Lead permissions, source edits/completion, stale
  edits, Guest denial and reversed dates. All six also pass with ERPNext/Pulse/CRM
  installed together, including no duplicate native Task on completion. Chrome
  editing/completion and reload now preserve title, status, priority and dates;
  CRM/project source filters behave correctly. Explicit project association
  remains pending. See crm-task-integration.md for installed-app browser evidence.
- Commercial project links: Chrome Administrator selection of a native customer
  and its draft sales order passed save/reload. Switching customer clears and
  filters orders; cancelling preserves saved links. See browser acceptance.
- Workload: Chrome allocation/leave creation passed. A 50% allocation for five
  weekdays displayed 20 available hours; one approved leave day reduced it to
  16. Earlier unassigned-estimate rendering and template cloning also passed.
- Workflow settings: added the missing status-order controls. Real Chrome
  rename/color/reorder/save/reload passed; list groups and Kanban columns follow
  the saved order. Build and focused UI detector pass.
- Task property UI: custom colored label creation/application and Milestone
  type persisted after reload. Configuring Bug/Task/Feature/Milestone constrained
  the reopened editor to those four choices. Activity showed actor/timestamp and
  type change. Subsequent UI refinement now names label additions/removals, both
  verified in Chrome; unavailable labels use an explicit fallback.
- Bulk task UI: two inline-created tasks accepted status/priority changes in one
  action, disappeared when archived, and survived restore/reload with values
  retained. Subsequent Chrome bulk assignment of both tasks also survived reload;
  CBA-1 activity shows the assignee, actor and timestamp. Relation-rich project
  moves remain a separate UI check.
- Relation-rich move regression: fixed stale derived project fields on incoming
  and outgoing Pulse Dependencies. Ten real-backend hierarchy cases pass,
  including direct native saves, rollback and idempotent repair of older records.
  The repair is wired into after_migrate and does not change dependency endpoints
  or timestamps. See runtime-validation.md.

These are focused additions, not a new full-suite completion claim.

Refreshed snapshot: **2026-09-16 19:08 UTC**, taken while parallel implementation was in progress. Source: every checkbox in [`BACKLOG.md`](../BACKLOG.md), expanded where a checkbox names multiple behaviors. This is a requirements/evidence inventory, not a completion claim or a replacement for the backlog. Later edits may resolve the gaps below.

Status meanings:

- **Implemented (tested path)**: source, runtime and applicable browser evidence establish the specifically described path. This does not extend to untested roles, variants or production migration.
- **Unverified**: a UI/API implementation is present, but evidence for the full named requirement remains incomplete; proven subsets are stated explicitly.
- **Partial**: a concrete part of the requested behavior is absent from the inspected source, even where other parts exist.
- **Missing**: neither an implementation nor usable path was found. No entire backlog area is missing.

A referenced test file is evidence of a definition unless its execution is recorded below. This audit read existing results without executing tests or changing implementation. `frontend/package.json` now defines `npm test` using Node test modules; root reports all seven TAP tests across three modules passed. This is helper/protocol regression coverage, not a browser test runner. Runtime validation remains owned by the runtime-validation workstream. The current runtime, realtime, redesign and three browser reports were inspected. Narrow proven paths are recorded below; broad requirements retain Unverified when material acceptance variants remain.

## Current evidence checkpoint

Refreshed 2026-09-16 19:05–19:08 UTC from current source, retained runtime logs and [runtime](runtime-validation.md), [HTTP/realtime](realtime-validation.md), [browser](browser-validation.md), [views](browser-views-validation.md), [docs/intake](browser-docs-intake-validation.md), [scheduling](view-scheduling-validation.md) and [UI redesign](ui-redesign-validation.md) reports. Later explicit passes supersede older negative or pending observations only for the same behavior.

- **Backend:** 101 integration cases passed in 52.227s. That combined command exited 1 because one of 44 unit fixtures incorrectly represented an unchanged task as a project move. Only the fixture changed; the complete 44-case unit rerun then passed in 15.145s. Retained `../.work/pulse-bench/pulse-tests.log` and `pulse-unit-tests.log` preserve both outcomes; do not describe the combined command as exit 0.
- **Subsequent focused backend:** business 7 passed; native-dependency views/analytics 8 passed; existing analytics 2 passed; sprint lifecycle/history 13 passed, including 201-task closure. Earlier focused hierarchy 7, task-flexibility 4, modules 4, views/preferences 3, scheduling 8 and task reorder 5 passed. Exact durations and logs are in the runtime report. These focused runs cover changes after the full integration run, not a new complete-suite pass.
- **Real HTTP/socket:** private upload/download and recipient-scoped comments/inbox/document updates, unauthorized access and membership revocation passed. Independent authenticated HTTP/Yjs editor smoke exited 0: concurrent paragraph convergence, compacted state/canonical HTML/fresh-reader reload, stale retry/metadata protection, read-only/outsider/guest/revoked denial and fixture cleanup. Its output was captured in tool session `85316`, not a retained log file (confirmed by docs delivery owner); script: `scripts/qa/document-collaboration-smoke.mjs`.
- **Actual collaborative browser editing:** two Chrome tabs edited the same page through contenteditable, converged with both `Editor A QA.` and `Editor B QA.`, and retained both after close/reload. Both tabs used the same Administrator account; distinct-user access is covered separately by HTTP smoke. Close-while-syncing now immediately displays canonical content, superseding the stale-reader defect. Revision history displayed five timestamped entries. See docs/intake report.
- **Actual task/view browser:** native creation, estimates, manual time/timer, comments, favorite/follow, status persistence, list reorder and immediate Kanban movement passed. Calendar date drag preserved duration; both timeline resize handles persisted dates. Calendar picker/date creation, Gantt/table/list inline creation, clipping retest, saved personal view filter/layout reload and grouped timeline Status headers passed. Other field/group/filter variants remain bounded by their row evidence.
- **Actual UI/reference browser:** all five layouts rendered, 390px navigation focus/Escape restoration and view icons passed, sprint panes scrolled independently, module creation/membership/scope and 50% completion transition passed. Kanban's latest optimistic drop and rollback helpers passed; real BQS-6 movement to Ready and back was observed in rebuilt preview.

Runtime remains isolated Frappe 16.34.0 / ERPNext 16.35.0, site `pulse-qa.localhost`. Earlier concurrent Task nested-set deadlocks were avoided through exclusive test windows; no production contention/load-capacity claim is made. No production migration or deployment occurred.

## Previously reported implementation gaps — resolved

1. Hierarchy moves now validate the complete final graph, require parent/descendant selection, sort parents before children and use native validation. `pulse/api/tasks.py::_hierarchy_order_for_move`, `task_config.py` and seven real hierarchy tests cover ordering, incomplete selection and rollback. The former selection-order finding is closed.
2. `pulse/services/dependencies.py` now merges permission-visible ERPNext `Task Depends On` and Pulse edges with direction/source metadata and deduplication; views and analytics use it. Eight real dependency cases and two analytics cases pass. The native-only-edge omission is closed.
3. `Views.vue` passes `groups` to `TaskTimeline.vue`; grouped row construction shares the date grid. Status grouping was actually observed with Backlog2/Ready1 and aligned bars. The ignored-Gantt-grouping finding is closed. All five grouping dimensions have source support; not every one has browser evidence.

Sprint hardening now covers immutable closure/history access and >200-task disposition; template cloning preserves labels/configuration and excludes templates from workload, with focused passes. These are no longer listed as missing implementation.

## Acceptance gaps reconciled with later browser evidence

The original snapshot below predates subsequent browser checks. The following
named gaps have newer evidence; this does not certify the entire corresponding
backlog area:

1. **Public intake:** guest submission, required-title validation, reviewer assignment,
   defer with preserved history, and disabled-token UI passed. Later Chrome
   rejection and duplicate decisions also preserved notes, original events and
   the duplicate reference across reload. See browser-docs-intake-validation.md.
2. **Sprints:** project-selector defect was fixed and creation, goal persistence,
   backlog drag, points measure, burndown rendering and Return to backlog closure
   passed. See browser-sprint-validation.md. Other closure UI variants remain
   bounded by their backend evidence.
3. **Commercial/template/workload:** customer/order save and reload, customer
   filtering, template cloning, unassigned hours, and allocation/leave capacity
   output now have browser evidence. See browser-validation.md.

Other explicit weak evidence remains in rows: global quick-create's earlier empty Project selector has no named successful unscoped retest; shared-view UI access, nested AND/OR combinations, column persistence, rich image/mention actions, and broad mobile/error states are not all signed off. These are specific acceptance limits, not blanket requests for all imaginable browser variants.

## 1. Foundation

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Native Project, Task, assignments and Timesheet as sources of truth | Unverified | `pulse/erpnext_bridge.py`, `pulse/api/spa.py`, `pulse/api/time.py`; `pulse/tests/test_native_time.py`, `pulse/tests/test_workflows.py` | Create/edit through Pulse, inspect native records and ToDo assignments, then read changes made through native ERPNext. |
| Preserve legacy data through migrations | Implemented (synthetic rehearsal) | `pulse/install.py`, `pulse/services/time_migration.py` retains source and uses provenance; migration is explicit/dry-run by default | Three real legacy Project/Task rehearsal cases pass (source/relationship preservation, idempotence and rollback); native time tests pass dry-run/retry/non-task preservation. Production legacy-schema equivalence remains unverified; no production migration was performed. |
| Consistent list, board, search, detail and API permissions | Unverified | `pulse/hooks/permissions.py`, `pulse/api/spa.py`; `pulse/tests/test_permissions_unit.py`, `pulse/tests/test_permissions_integration.py` | Restricted-user ORM/API tests and HTTP attachment/notification boundaries pass; verify corresponding restricted-user browser list/board/search/detail behavior. Passing tests cover named boundaries, not every possible REST surface. |
| Real attachments, comments, notifications and realtime | Unverified | `TaskDrawer.vue`, `Board.vue`, `Inbox.vue` under `frontend/src`; `pulse/api/spa.py`, `pulse/api/personal.py`, `pulse/api/notify.py` | HTTP/socket report passes private file and notification access including revocation; task comment persistence passes in browser. Still observe visible second-session board refresh and attachment controls through browser. |
| Accurate blocked dependencies, review semantics, project scope and authorized analytics | Unverified | `pulse/services/analytics.py`, `pulse/api/analytics.py`; `pulse/tests/test_analytics_unit.py` and `pulse/tests/test_analytics_integration.py` cover deduplication, hidden/resolved blockers, custom states and cancelled tasks | Native+Pulse dependency merge and blocked analytics now pass eight focused cases plus two existing analytics cases. Project/category/archive and scoped reports also pass. Reconcile actual analytics UI totals with a known fixture before UI acceptance. |

## 2. Flexible tasks

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Project status names, colors and order | Unverified | `pulse/api/task_config.py`; `frontend/src/components/tasks/TaskSettings.vue`; `pulse/tests/test_task_config_unit.py`, `pulse/tests/test_task_flexibility.py` | Unused To Do → Ready rename and later In Progress task persistence passed in browser. Custom color/order and other native mapping variants still require checks. |
| Configurable task, bug, feature and milestone types | Unverified | Same configuration API/UI; `test_disallowed_type_rejected` in `test_task_config_unit.py` | Configure all requested types, create/edit tasks, reload, reject disallowed type. |
| Colored labels, hour/point estimates, start/due dates | Unverified | `task_config.py`, `TaskSettings.vue`, `frontend/src/components/TaskDrawer.vue`; validation tests in `test_task_config_unit.py` | 3 hours / 5 points persisted in browser; label creation displayed default blue. Applying labels/custom colors and start/due UI persistence remain untested; runtime validation covers invalid estimates/dates/foreign labels. |
| Rich descriptions: images, code blocks, mentions | Unverified | `TaskDrawer.vue` embeds frappe-ui `TextEditor`, mention options and private upload arguments | Real toolbar/editor entry, authenticated image upload, code formatting and mention delivery; save/reopen round trip. Installed frappe-ui source contains ExtendedCodeBlock, ImageExtension and MentionExtension. `pulse/tests/test_task_rich_activity.py` passed the rich HTML/Version round trip; real editor/image/mention delivery remains to verify. |
| Field and assignment activity | Unverified | `pulse/api/tasks.py::activity/record_assignment`, `pulse/install.py` enables Task change tracking; `TaskDrawer.vue`; all 4 `test_task_rich_activity.py` cases passed, including native removal/deletion history | Update a field and native assignment in each entry path; verify actor, event and order in UI. |
| Bulk edit, move, assign and archive | Unverified | Atomic `pulse/api/tasks.py::bulk_update`; Board now has multi-selection, status/priority/project/assignment and archive/restore controls; four `test_task_flexibility.py` cases passed | Hierarchy ordering/complete-selection/rollback now pass seven real cases, plus four flexibility cases. Multi-selection edit/assign/move/archive controls exist; no complete browser bulk workflow is retained. |
| Preserve subtasks, dependencies, checklists and comments | Unverified | `TaskDrawer.vue`, `pulse/api/spa.py`; `test_workflows.py`, `test_task_flexibility.py::test_archive_keeps_task_and_its_children` | Archive/migration and hierarchy-safe moves preserve covered relations; native dependencies now merge visibly; task comment persisted in browser. Full relation-rich bulk UI round trip remains unobserved. |

## 3. Views

Calendar/timeline/spreadsheet UI is `frontend/src/pages/Views.vue`, now embedded alongside Board/List in `frontend/src/pages/Board.vue`; the API is `pulse/api/views.py`. Board pointer-grip reorder is a different gesture path from Views native date dragging.

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Calendar drag rescheduling | Implemented (tested path) | Calendar drop handler plus `schedule_tasks`; real browser BQS-2 date shift and eight scheduling tests | Real Sept18→19 drag preserved two-day duration and returned saved dates; calendar picker scheduling also passed. Denied-user browser recovery remains untested. |
| Timeline/Gantt resizing and dependency links | Unverified | Pointer resize handles and SVG dependency paths; dependency action controls | Both date resize handles and inline creation passed; clipping retest passed. Native+Pulse edges now merge with eight focused tests. Actual dependency creation/arrow rendering still lacks a retained browser pass. |
| Spreadsheet inline editing | Unverified | Per-field inputs/selects and `edit` mutation | Title inline edit has observed `Task updated.` and persisted row. Other fields, date input behavior and rejection recovery still require browser confirmation. |
| Group by status, assignee, priority, project and label | Unverified | `groupFields` and computed `groups` include all five | Calendar/spreadsheet and Gantt now use groups. Real Gantt Status grouping showed Backlog2/Ready1 and aligned bars. Assignee/priority/project/label grouping is source-implemented but lacks retained browser execution. |
| Show/hide/reorder columns | Unverified | Checkbox controls and move-up/down controls | Change order/visibility and restore after reload/saved view open. |
| Nested AND/OR filters | Unverified | `frontend/src/components/views/FilterGroup.vue`, `pulse/services/view_filters.py`; `tests/test_view_filters.py` | Simple Title contains filter passed in browser; nested AND/OR result semantics and bounded invalid-tree behavior still need combined runtime/UI evidence. |
| Saved personal/shared and cross-project views | Unverified | `save_view`, `saved_views`, saved-view permission hooks and broad task query | Three focused view tests pass ownership/spoof rejection/scoped preferences. Personal QA inline work view restored Spreadsheet, Title filter and three rows after reload. Shared-view access and cross-project UI restoration remain unobserved. |
| Per-user filter/layout preferences | Unverified | `preferences` API and watched configuration persistence | Focused tests pass user/project/editor isolation and ordering/weekend settings; personal saved-view layout/filter reload now passed. Independent unsaved per-user preferences and column order/visibility reload still lack explicit browser results. |

## 4. Sprints

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Drag backlog-to-sprint planning | Unverified | `frontend/src/components/sprints/SprintPlanner.vue`, `pulse/api/planning.py::move_to_sprint`; `test_sprint_planning.py` | Real drag both directions, button fallback, saved membership and access errors. |
| Goals and estimated workload | Unverified | `frontend/src/pages/Sprints.vue`, `planning.py::configure_sprint/sprint_progress` | Save goal and show summed hours/points for known sprint tasks. |
| Task-count, hours or points progress | Unverified | `planning.py::sprint_progress`, Sprints controls | Change measure and verify numerator/denominator with known completed/open effort. |
| Historical burndown from recorded scope and effort changes | Unverified | `pulse/api/sprint_history.py`, sprint event records; `tests/test_sprint_metrics.py` | Run replay tests and real lifecycle integration; add/remove/reestimate/reopen on recorded dates and inspect chart. |
| Explicit unfinished handling and frozen closure summary | Unverified | `planning.py::close_sprint`; `pulse/tests/test_sprint_planning.py` covers carryover, frozen dates/goal/effort and invalid transitions | Close in UI with each disposition; verify moved work and immutable summary after later Task edits. |

## 5. Intake

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Incoming requests separate from tasks | Unverified | `pulse/api/intake.py`, `frontend/src/pages/Intake.vue` | Real browser created Incoming request and Created history; seven intake integration tests establish separation. Browser did not independently inspect native task absence before acceptance. |
| Accept/reject/defer/duplicate and reviewer assignment | Unverified | Intake UI and review APIs; `pulse/tests/test_intake.py` | Each transition in UI, reviewer permissions, duplicate cycle rejection, unauthorized direct edits. |
| Accepted conversion preserves history | Implemented (tested path) | `accept_request`; `test_accept_is_idempotent_and_retains_source_history`, direct-forgery test | Real browser acceptance created TASK-2026-00032/BQS-4 and retained Created/Accepted history and review note. Runtime idempotence and direct-forgery cases passed; duplicate click behavior in browser remains untested. |
| Public request forms after core intake | Unverified | `pulse/api/public_intake.py`, `pulse/www/pulse-request.html`, `pulse/www/pulse-request.py`; Intake admin enable/title/instructions/share controls now present; seven intake integration cases passed | Root confirms guest page rendered and empty-title native validation; successful guest submit is pending the DB window. Enable/disable/token rotation and absence of private project exposure still require final browser evidence. |

## 6. Documentation

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Rich project pages and task links | Unverified | `frontend/src/pages/Documents.vue`, `pulse/api/documents.py`; `pulse/tests/test_documents.py` | Brief page creation, rendered headings, correct task link and cross-tab persistence passed. Editing rich body, navigating backlinks and restricted-role browser behavior remain unverified; cross-project rejection has runtime coverage. |
| Documentation search | Unverified | `documents.py::list_pages` queries title/content; test template/search case | Known body/title matches from authorized projects only through UI. |
| Page comments and mentions | Unverified | Documents discussion editor, `add_comment`, `pulse/pulse/doctype/pulse_document/pulse_document.py::safe_mentions` | Add real comment, confirm authorized mention notification and persistence; denied mentions excluded. |
| Revision history | Unverified | `documents.py::revisions`, Documents revision UI; `test_template_search_revision_and_conflict` | Actual browser showed five Administrator timestamp entries after shared edits; API revision/conflict cases pass. Individual prior/new change disclosures were not explicitly expanded in recorded acceptance. |
| Brief, meeting-note and specification templates | Unverified | `documents.py::TEMPLATES` contains all three | Brief template creation/save passed in browser. Meeting and specification templates and subsequent edits remain untested in browser. |
| Collaborative editing | Implemented (tested path) | `frontend/src/components/documents/CollaborativeEditor.vue`, `frontend/src/utils/documentSync.js`, `documents.py::sync_page`; Yjs dependencies present | Two actual Chrome editors converged with both edits and retained content after close/reload; immediate close during sync refreshed canonical reader. Distinct-user HTTP smoke passed retry/metadata and permission/revocation boundaries. Both browser tabs used Administrator; long offline sessions/load behavior are not established. |

## 7. Everyday usability

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Global task/project/page search | Unverified | `pulse/api/personal.py::search`, `frontend/src/components/CommandPalette.vue` | Search all three entity types as restricted user and navigate results. |
| Command palette and keyboard shortcuts | Unverified | `CommandPalette.vue`, `frontend/src/App.vue` implements Ctrl/Cmd-K, N and Escape handling | Actual keyboard focus, arrow/enter/escape behavior, editable-field and modal safeguards. |
| Read/unread inbox and task following | Unverified | `frontend/src/pages/Inbox.vue`, `PersonalControls.vue`, `pulse/api/personal.py` | Follow task; another user changes/comments; notification appears only for eligible recipients, read/unread persists. |
| Favorites and genuinely recently opened items | Unverified | `personal.py::remember/items`, task/page controls, Projects favorite controls with `record-recent=false`, App project-route watcher and palette activation | Verify opening through every supported route records recency without list rendering doing so; favorites persist. Both personal integration tests now pass, including revocation. Task favorite/follow persisted in browser; project/page favorites and recent-order behavior still need browser checks. |
| Quick task creation anywhere | Unverified | Global `CreateIssueModal` in `App.vue`, N shortcut and global new button | Scoped Board creation passed. Earlier unscoped Work views empty Project selector has no explicit successful retest after current loader/fallback/retry source changes; prove global and mobile entry points and failure recovery. |
| Responsive mobile layout | Unverified | Mobile App sidebar and responsive page/layout CSS | 390px navigation focus containment/Escape restoration and five layout icons passed. Actual drawers/editor/forms/date gestures and other new screens at narrow widths remain unverified. |
| Empty/loading/recoverable-error states | Unverified | App error boundary, Skeleton/page states; TaskDrawer now exposes `attachmentError`, `activityError`, retry buttons and deletion failure toast | One task-details Retry successfully recovered in browser. Force attachment/activity/save failures and verify retained input and accurate empty/loading/error states across remaining surfaces. |

## 8. Business integration

| Requirement | Status | Source and existing test definitions | Evidence still required |
|---|---|---|---|
| Customer and sales-order project links | Unverified | `pulse/api/business.py::_links/update_project/commercial_options`, `frontend/src/pages/Projects.vue` | Real Customer/Sales Order choice/save/reload and mismatched customer/unauthorized order rejection. |
| Native Timesheets, manual entry and task timer | Implemented (tested path) | `pulse/api/time.py`, `frontend/src/components/TaskTime.vue`; `pulse/tests/test_native_time.py` | Browser saved 0.5h billable manual time to TS-2026-00003 and stopped timer into nonbillable TS-2026-00004; 11 native-time integration tests pass. Durable timer reload and restricted-role browser variants remain untested. |
| Estimated vs actual, billable vs nonbillable | Implemented (tested path) | `time.py::get_time_summary`, TaskTime summary; native time test | Browser showed 0.50 actual / 3.00 estimated, 0.50 billable / 0.00 nonbillable after manual entry; timer added nonbillable draft time. Native summary tests pass. Longer mixed submitted/draft UI totals remain untested. |
| Repeatable project templates | Unverified | `business.py::clone_template`, Projects template controls | Clone representative project twice; inspect native hierarchy/dependencies/checklists/config and rollback failure. Seven focused business cases now pass, including clone labels/configuration, structure/reset and template workload exclusion; actual clone workflow remains unverified. |
| Workload using hours and availability | Unverified | `business.py::capacity_hours/workload`, Projects workload table | Known active allocations, approved overlapping leave, dates and shared assignments produce exact displayed capacity/load; restricted-user behavior. Eight-hour weekdays and full overlapping-task estimates are explicitly the current implementation basis. |

## Additional user UI/reference requirements

These six items are explicitly recorded in BACKLOG.md in addition to the original eight areas. Source support plus selected visual checks does not establish every interaction.

| Requested behavior | Current source/evidence | Remaining acceptance |
|---|---|---|
| Plane-style calendar: weekday option, date add menu, prefilled create, searchable multi-select scheduling, compact cards, persistent preferences | `Views.vue`, calendar picker, scheduling/preferences API. Browser passed weekday display, date menus, single searched-task scheduling, date-prefilled create and duration-preserving drag; eight scheduling tests pass. | Actual multi-selection scheduling and calendar preference reload are not explicitly recorded. |
| Kanban reference: property chips, collapse, always-available creation, insertion markers | `Board.vue`, inline task editor and pointer/optimistic movement helpers. Actual move/reorder and rebuilt immediate drops pass; delayed-save/rollback tests pass. | Editable chip persistence, collapse restoration and context defaults are not all demonstrated in retained browser report. |
| List status group header plus and New task footer with context defaults | `Board.vue` and `InlineTaskCreate.vue`; Ready header plus created List inline QA in Ready; Escape closed editor. | Footer creation and its group defaults have source support without a named browser pass. |
| Table: sticky identity, inline selectors, searchable columns, semantic ascending/descending sort | `TaskSpreadsheet.vue`, Views display/sort configuration. Title edit and footer inline creation passed in browser; source includes requested controls. | Selector changes, searchable column visibility/order persistence and semantic sort behavior lack an explicit browser result. |
| Timeline: Week/Month/Quarter, Today, expand, sticky task/duration, today marker, date creation | `TaskTimeline.vue` implements controls; actual creation, resize, clipping retest and grouped rows passed. | Zoom/Today/expanded and keyboard date-add behavior are not separately demonstrated in retained browser report. |
| Modules: many-to-many membership, metadata, live completion, scoped layouts/creation | `pulse/api/modules.py`, module UI, TaskDrawer membership. Four integration cases pass; browser created module, added two tasks, navigated scoped layout and observed completion change to 50%. | Module-aware inline creation, metadata editing and removing membership remain without named browser results. |

Plane-inspired shell, compact controls, focus behavior and independent pane scrolling are supported by the UI report. The user's visual references are design targets, not a claim of pixel-identical reproduction. No full-backlog completion is claimed by this matrix.

## Completion evidence to attach before checking backlog boxes

1. Record exact source revision, runtime/site versions and migration state, test command, timestamp, result counts and retained log path for each real-backend run. Test definitions or builds cannot substitute for passing execution.
2. Record real browser scenarios with role, viewport, interactions, persisted result and screenshot/log artifact. Include task configuration and relationships, all views, sprint drag/close, intake/public forms, concurrent docs, inbox/search/shortcuts and business/time flows.
3. Preserve the passing runtime checkpoint and use focused checks for subsequent changes; record new regressions explicitly. Exercise restricted users and a second simultaneous session for privacy, notifications, realtime and collaboration. An Administrator-only happy path cannot prove these requirements.
4. Reconcile stale historical observations against later explicit evidence. Promote **Unverified** only when the cited runtime and UI evidence actually covers the row; retain limitations and failures explicitly.
