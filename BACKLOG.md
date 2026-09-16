# Pulse implementation backlog

Branch: `codex/erpnext-backlog`. Base: `96859dd`. Unchecked items are not complete, including where upstream has partial schemas/UI. Completion requires usable UI/API and appropriate validation on real Frappe/ERPNext.

## 1. Foundation
- [ ] Native ERPNext Project/Task/assignments/Timesheet sources of truth; preserve legacy data with migrations.
- [ ] Consistent list, board, search, detail and API permissions, including restricted-user integration tests.
- [ ] Real-backend attachments, comments, notifications and realtime verification.
- [ ] Accurate analytics: blocked dependencies, review semantics, project scope, authorized aggregates.

## 2. Flexible tasks
- [ ] Project status names, colors and ordering.
- [ ] Configurable types including task, bug, feature and milestone.
- [ ] Colored labels, points/hour estimates, start and due dates.
- [ ] Rich descriptions with images, code blocks and mentions.
- [ ] Field and assignment activity history.
- [ ] Bulk edit, move, assign and archive.
- [ ] Preserve subtasks, dependencies, checklists and comments.

## 3. Views
- [ ] Calendar drag rescheduling.
- [ ] Timeline/Gantt date resizing and dependency links.
- [ ] Spreadsheet inline editing.
- [ ] Group by status, assignee, priority, project or label.
- [ ] Show/hide/reorder columns.
- [ ] Nested AND/OR filters.
- [ ] Saved personal/shared and cross-project views.
- [ ] Per-user filter/layout preferences.

## 4. Sprints
- [ ] Drag backlog-to-sprint planning.
- [ ] Goals and estimated workload.
- [ ] Task count, hours or points progress.
- [ ] Historical burndown based on recorded scope and effort changes.
- [ ] Explicit unfinished-work handling and frozen closure summaries.

## 5. Intake
- [ ] Incoming requests separated from accepted tasks.
- [ ] Accept, reject, defer, duplicate; assign reviewers.
- [ ] Convert accepted requests preserving history.
- [ ] Public request forms after core intake.

## 6. Documentation
- [ ] Rich project pages and task links.
- [ ] Documentation search.
- [ ] Page comments and mentions.
- [ ] Revision history.
- [ ] Brief, meeting-note and specification templates.
- [ ] Collaborative editing after core documentation.

## 7. Everyday usability
- [ ] Global task/project/page search.
- [ ] Command palette and keyboard shortcuts.
- [ ] Read/unread notification inbox and task following.
- [ ] Favorites and genuinely recently opened items.
- [ ] Quick task creation from anywhere.
- [ ] Responsive mobile layouts.
- [ ] Empty, loading and recoverable error states.

## 8. Business integration
- [ ] Customer and sales-order project links.
- [ ] Native ERPNext Timesheets with manual entries and task timer.
- [ ] Estimated vs actual hours; billable vs nonbillable.
- [ ] Repeatable project templates.
- [ ] Workload based on hours and availability.

## Evidence log

- Source inspection: native Project/Task already used by upstream code; upstream standalone README/charter stale. Canonical contract corrected; native time consolidation pending.
- Initial analytics unit tests cover review vs blocked, dependency deduplication, completed/invisible blockers and cancelled work. Real permission-scoped endpoint validation pending.
- Parallel work in progress: permission enforcement, historical sprint backend, isolated real-backend setup.

### Foundation implementation checkpoint

- Native time API now writes draft ERPNext Timesheets, rejects user impersonation and invalid durations, and provides visible billable/actual summaries. Persistent per-user timer start/stop and TaskTime drawer controls implemented; real integration/browser validation pending.
- Legacy time migration performs a dry run by default, retains source records and adds unique entry provenance. Explicit execution required after review; native overlap validation retained.
- Permissions agent added shared checked-document helper, permission-aware lists, scope hooks, private realtime recipients, and time-history deletion protection. 6 pure policy regressions pass; direct REST/integration coverage remains unrun.
- Sprint backend and planning UI implemented by parallel agent; recorded scope replay has 4 passing pure regression tests. Real endpoint/drag-and-drop/closure verification pending.
- Analytics has 3 passing pure regressions. All 13 pure tests passed together in this checkpoint; Python syntax compilation passed. This does not establish full feature completion.
- Runtime setup lives outside checkout at `../.work/pulse-bench/RUNTIME.md`: isolated MariaDB/Redis and official Frappe/ERPNext v16 sources. Dependency installation ongoing; no real-backend test pass claimed.
- Parallel next work: configurable task backend and bulk actions; sprint UI build; real runtime installation. Root owns time integration and TaskDrawer.

### Integration and design checkpoint — 2026-09-16

- Real Frappe 16/ERPNext 16 run: 71 integration tests and 38 additional tests passed. Latest migration rollback unit suite independently passed all 7 tests. See `docs/runtime-validation.md` for exact commands, environment and limits.
- Actual HTTP/Socket.IO smoke passed comments, inbox delivery, native uploads/private downloads, unrelated-user isolation and membership-revocation behavior. See `docs/realtime-validation.md`.
- Browser checks proved task/project creation, estimates, favorites/following, comments, manual time and timers; remaining feature-by-feature UI acceptance is still required.
- Additional user request: major Plane-inspired visual and organizational redesign. Contract recorded in `PRODUCT.md` and `DESIGN.md`: grouped workspace/project navigation, compact neutral surfaces, contextual tools, progressive disclosure and mobile support. All original backlog functions remain required.
- Current visual build passes. Root desktop/mobile review is finding and fixing navigation density, duplicate primary actions, date presentation and focus behavior before final signoff. Browser changes require fresh acceptance; previous screenshots do not prove the redesign.

## Additional user reference requirements (September 16)
- [ ] Calendar matches supplied Plane screenshots: weekday option, date add menu, date-prefilled new task, searchable multi-select existing task scheduling, compact cards and persistent preferences.
- [ ] Kanban matches reference columns/cards with editable property chips, collapse, always-available new task and clear insertion markers.
- [ ] List status groups include header plus and New task footer with context defaults.
- [ ] Table matches reference sticky task identity, inline selectors, searchable column display and semantic ascending/descending ordering.
- [ ] Timeline matches reference Week/Month/Quarter zoom, Today, expanded mode, sticky task/duration, today marker and hover/focus date creation buttons.
- [ ] Project Modules support many-to-many task membership, metadata and live completion percentages, plus module-scoped task layouts and creation.

### Acceptance follow-up — 2026-09-16
- Guest public intake submission, required title validation, reviewer assignment/deferral history, and disabled-link rejection now verified through actual unauthenticated/admin browsers. QA form disabled afterward.
- Acceptance exposed older-project loss in shared EntityForm. Fixed selected-value retention, bounded searchable link options and field label associations; rebuilt and verified in New Sprint.
- Added a standard frontend test command (`npm test --prefix frontend`): all seven TAP cases pass across drag persistence/rollback, timeline date/group geometry and collaborative document convergence.
- Expanded commercial integration run retained seven passes but two new fixture setup errors; these did not reach product assertions and are being corrected. Full goal remains active; see verification matrix for precise remaining evidence.

## Additional live-reference requests
- [ ] Minimal inline creation in List, Kanban, Calendar and Table with project key and Enter-to-add-another behavior.
- [ ] Consistent clean status/priority/assignee/layout icons.
- [ ] Gantt hover/focus task preview and circular resize handles.
- [ ] Calendar Month/Week layouts and weekend toggle, date-cell hover Add work item; remove nested Edit dates scroll panels.
- [ ] Table creation pinned to bottom of workspace viewport.
- [ ] Full-screen task detail with project/work-item/task breadcrumbs.
- [ ] Remove large Analytics toolbar button; retain access through menu.
- [ ] Pages reader/editor fills available pane width and height.

Actual Plane List, Kanban, Calendar, Spreadsheet and Gantt inspected in Chrome; see docs/plane-live-reference.md. These newer UI acceptance items remain distinct from earlier successful tests until combined build/browser verification.
