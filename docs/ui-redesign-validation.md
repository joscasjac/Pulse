# Plane-inspired redesign validation

User requested a major visual and organizational revamp based on makeplane/plane. Root inspected the official repository and Plane's actual product screenshot at plane.so, then implemented the original Pulse design contract in PRODUCT.md and DESIGN.md.

## Completed implementation

- Light neutral workspace, compact controls and theme-aware semantic status colors.
- Separate personal/workspace navigation, six prioritized projects, project tabs and advanced tools under More.
- Redesigned Home, My work, Projects, Tasks, Views, Pages, Intake, Sprints, Backlog, Inbox and time entry surfaces.
- Secondary settings disclosed on demand; context-specific primary actions.
- Mobile navigation focus containment/restoration and modal task drawer focus management.

## Observed browser evidence

- Real authenticated desktop shell, task board, task drawer, Views timeline and Home rendered after production rebuild.
- Changing BQS-1 status to In Progress persisted and moved its card/column counts on the real backend.
- Desktop review identified and fixed duplicate primary actions, long sidebar project list, raw datetime display and search input icon overlap.
- At 390px viewport the mobile menu transferred focus into navigation, hid the workspace accessibility tree, and Escape restored focus to its opening button. Viewport reset after check.
- Main frontend build passed; Vue compilation passed on redesigned surfaces. Static design detector passed root CSS, Inbox and status component and agent-owned surfaces.
- Independent finish review identified priority vocabulary, project-list refresh, modal focus and competing primary actions; those source fixes landed.

## Remaining scope

Full original backlog acceptance remains tracked separately in verification-matrix.md. In particular, a rendered screenshot does not prove all calendar/Gantt interactions, every shared-view permission, collaborative editing in two browser sessions, or all new-screen mobile layouts. No full-goal completion is claimed here.

## User feedback refinement, September 16
- Unified all five task layouts with collapsed Filters/Display and selection-only bulk actions; removed duplicate creation action and redundant scoped project selectors.
- Slim task drawer and creation dialog; secondary properties/tools are disclosures. Compact Pages toolbar/list/reader.
- Shared 15px rounded checkboxes, visible inactive view icons, independent split-pane scrolling in Sprints, Intake and Pages.
- Real browser: BQS-2 list grip reordered before BQS-1, success toast observed, order survived reload. Kanban grip moved BQS-2 into empty Ready column with success toast and counts. Native-only dragging was inconsistent under automation; explicit pointer grips now provide reliable movement.
- Five real backend move_task tests pass; frontend drag helper assertions pass. Final builds pass.
- Browser measured sprint list and detail each at 453px, with scroll heights3192/963; scrolling detail changed its scrollTop to510 while list and workspace remained0.
- All five layouts rendered with project scope. 390px toolbar exposed all five icons with readable contrast. Calendar month boundaries tested for four cases including leap February.
- Calendar outer/inner class collision found during visual QA and corrected before delivery.
- Original backlog acceptance remains separate; these checks do not imply every feature or gesture has complete end-to-end coverage.

### Project modules (2026-09-16)

Modules are project-scoped groupings of canonical ERPNext Tasks. A task may belong to multiple modules. Module completion is the number of visible, non-archived Tasks with native Completed status divided by visible, non-archived, non-Cancelled Tasks; an empty module shows 0%. The UI states these visibility and denominator rules. No inaccessible task counts or task names enter module progress.

The Modules page supports creation and metadata editing (title, description, status, dates, lead), adding/removing existing tasks, module-aware task creation, and a link to all five task layouts filtered to the module. The task drawer supports multiple module memberships. Moving a native Task to another project removes its old module memberships transactionally. New standalone module/link DocTypes preserve Task and Project as source of truth; no legacy data migration is required beyond normal DocType schema sync.

Component SFC compilation passed. Schema migration and all four real-backend module tests passed (progress/exclusions/multiple memberships, guest access/date validation, junior hidden-task isolation, and project-move cleanup). This note does not claim browser acceptance.

## Modules browser follow-up

Created `QA release module` (hvlshoils4) in PROJ-0035. Empty progress displayed 0% / 0 of 0. Added BQS-2 and BQS-3 through picker; detail showed both native task links and 0% / 0 of 2. Full task view link preserved project and module scope. Completion percentage transition and inline creation remain to validate.

## Drop refresh refinement

Built inline/toolbar changes successfully (pulse-inline-build.log). Actual pointer-grip drag BQS-4 from Backlog to empty Ready completed successfully in rebuilt preview, with Ready1/Backlog0 and success message. Refresh is deferred during drag/save; indicator uses non-flow overlay; ordinary background loads retain board instead of skeleton. Task layout helper tests passed. Fine animation smoothness still benefits from user observation on their input device.

Modules refresh retest: after one of two member tasks became Done, Modules list displayed 50% for QA release module. This verifies visible completion percentage from current member states.

### Kanban immediate-drop follow-up
- Local rows now move before awaiting the server, with exact rollback on rejection. Drag start invalidates pre-gesture board requests so stale responses cannot undo the visual move.
- Delayed-save regression confirms destination placement before the promise resolves; rejected-move rollback and pointer tests pass. Production build passes.
- Real browser: dragged BQS-6 from Backlog to Ready and back to its original position after loading the rebuilt bundle. Both drop destinations were verified in the rendered board. Server remained reachable on port 18016.

### Entity form older-project fix acceptance
New sprint under PROJ-0035 initially lost its prefilled project because only the newest 50 link options were returned. Shared EntityForm now retains an authorized selection outside the initial page and provides bounded search/pagination. After production rebuild and HTTP restart, actual browser New Sprint showed Browser QA September selected, associated field labels, and Save enabled after entering a sprint name. Search Project for Browser QA reduced options to that project. Form cancelled without writing a sprint during the concurrent integration-test window. Two focused unit tests and read-only real-bench selected-value lookup passed. Full sprint lifecycle remains pending.
