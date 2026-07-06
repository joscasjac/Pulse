# Pulse — Functional Requirements

**Document 4 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).
**Status:** Specification. Conforms to `_canonical-model.md` (single source of truth) and `00-Pulse-Enterprise-Analysis.md`.

---

## How to read this document

This is the **exhaustive functional specification** for Pulse. It enumerates every user-facing and system behaviour as a numbered requirement, grouped by functional area. Each requirement carries:

- **ID** — stable identifier (e.g. `FR-BOARD-001`) usable in traceability, tests, and PR descriptions.
- **Requirement** — the behaviour, described concretely.
- **R/E/B** — the reuse tag: **Reuse** (use ERPNext/Frappe as-is), **Extend** (custom field / workflow / fixture / permission hook over core), **Build** (new doctype / report / SPA — still over core data).
- **Reused component** — the specific ERPNext/Frappe doctype, view, or service leaned on.
- **Mechanism** — *how* it is delivered (custom field, workflow, fixture, doc-event, permission hook, script/query report, dashboard chart, whitelisted API, Kanban Board, SPA view).
- **Acceptance criteria** — the observable, testable condition of "done".
- **Priority** — MoSCoW (**M**ust / **S**hould / **C**ould / **W**on't-this-release).
- **Phase** — 1 (Reuse-First MVP), 2 (Modern Experience), 3 (Portfolio & Ecosystem), per canonical §10.

**Naming reminders (binding):** App = **Pulse**. The card **is** an ERPNext **Task**; the project **is** an ERPNext **Project**. The only new doctypes are **Pulse Sprint**, **Pulse Task Status Log**, **Pulse Settings**, **Pulse Role Rank**. Custom fields use the `pulse_*` prefix. No core-file edits; all additions ship as fixtures.

### Reuse-tag summary

| Tag | Count of requirements | Meaning |
|---|---|---|
| **Reuse** | 41 | ERPNext/Frappe capability used unchanged |
| **Extend** | 58 | Custom field / workflow / fixture / permission hook over core |
| **Build** | 61 | New doctype, report/chart, or SPA view (over core data) |
| **Total** | **160** | across 18 functional areas |

---

## 1. Projects

Reuse ERPNext **Project** as the container. Agile behaviour is opt-in per project via custom fields; templates and membership reuse core.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-PROJ-001 | A user with create permission can create a Project (name, company, customer, dates) using standard ERPNext. | Reuse | Project | Desk form / REST | New Project persists with core costing/billing fields intact; no Pulse fields required to save. | M | 1 |
| FR-PROJ-002 | A Project can be flagged agile via **Enable Scrum**. | Extend | Project | Custom field `pulse_enable_scrum` (Check), fixture | Toggling on surfaces Pulse agile UI (board/backlog/sprints) for that project; off hides them. | M | 1 |
| FR-PROJ-003 | A Project stores a **Board Type** (Scrum/Kanban). | Extend | Project | Custom field `pulse_board_type` (Select: Scrum,Kanban), fixture | Value defaults from Pulse Settings and drives board mode (sprint-scoped vs continuous). | M | 1 |
| FR-PROJ-004 | A Project stores a **Default Sprint Length (days)**. | Extend | Project | Custom field `pulse_default_sprint_length` (Int), fixture | Field defaults from Pulse Settings; used to pre-fill new sprint end dates. | S | 1 |
| FR-PROJ-005 | A Project can carry a short **Project Key** (e.g. "PLS") for card references. | Extend | Project | Custom field `pulse_project_key` (Data), fixture | Key is stored and displayed on cards as `KEY-<task no>`; optional, blank allowed. | S | 2 |
| FR-PROJ-006 | Project agile custom fields are grouped under a **Pulse** section on the Project form. | Extend | Project | Custom field `pulse_section` (Section Break), fixture | Fields appear together in one collapsible section; no clutter on non-agile projects. | S | 1 |
| FR-PROJ-007 | A Project can be created from a **Project Template**, generating its task structure. | Reuse | Project Template / Project Template Task | Core template apply | Applying a template creates the tasks; Pulse fields on generated tasks default sensibly. | S | 1 |
| FR-PROJ-008 | Sprint/epic scaffolding can be captured as reusable **Project Templates**. | Reuse | Project Template Task | Fixture examples + docs | Ships example templates; instantiating produces expected task tree. | C | 2 |
| FR-PROJ-009 | Project members are managed via the **Project User** child table. | Reuse | Project → Project User | Core child table | Adding a Project User grants that user visibility per standard Project permissions. | M | 1 |
| FR-PROJ-010 | Project membership scopes what the user sees in Pulse views. | Extend | Project User / User Permission | `permission_query_conditions` | A user not on the project (and without elevated role) cannot list its tasks/board. | M | 1 |
| FR-PROJ-011 | Project financial fields (costing, billing, margin) remain visible/editable only to finance roles. | Extend | Project | `permlevel` on fields | Delivery roles see delivery fields; costing fields are read-only/hidden to them. | M | 1 |
| FR-PROJ-012 | Project health/status can be captured via **Project Update**. | Reuse | Project Update | Core doctype | Creating a Project Update records health; surfaced in Pulse project header (Phase 2). | S | 1 |
| FR-PROJ-013 | A modern Project overview (progress, sprint, members, health) renders in the SPA. | Build | Project + Task + Pulse Sprint | SPA view + whitelisted API | Overview loads project summary in one lean call; ≤1s for a 500-task project. | S | 2 |
| FR-PROJ-014 | Archiving/closing a Project uses core Project status; Pulse hides closed projects by default. | Reuse | Project (status) | Core status + SPA filter | Closed projects excluded from default Pulse lists; reachable via filter. | C | 2 |

---

## 2. Work Items / Tasks (Cards)

The card **is** an ERPNext **Task**. All CRUD, timeline, comments, attachments come from core; Pulse adds agile fields.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-TASK-001 | A user can create a card (Task) with subject, project, type, priority, dates. | Reuse | Task | Desk form / REST / SPA quick-add | Task persists against a Project; appears in that project's board/backlog. | M | 1 |
| FR-TASK-002 | A card supports a rich-text description. | Reuse | Task `description` (Text Editor) | Core field | Formatting, links, images persist and render in Desk and SPA. | M | 1 |
| FR-TASK-003 | A card can be edited (subject, description, priority, dates, assignees). | Reuse | Task | Desk / SPA / REST | Edits persist with standard validation and Version history. | M | 1 |
| FR-TASK-004 | A card supports file **attachments**. | Reuse | File / Attachments | Core attach | Files attach to the Task and list in the card detail; permissions respected. | M | 1 |
| FR-TASK-005 | A card supports **comments**/discussion. | Reuse | Comment / Communication | Core timeline | Comments post to the Task timeline and notify participants. | M | 1 |
| FR-TASK-006 | A card records a full **activity timeline / audit** of changes. | Reuse | Activity Timeline / Version | Core | Field changes and events are visible on the Task; no custom audit code. | M | 1 |
| FR-TASK-007 | Sub-tasks are modelled via **parent_task**. | Reuse | Task `parent_task`, `is_group` | Core hierarchy | Creating a child Task with parent set nests it; parent shows children. | M | 1 |
| FR-TASK-008 | A card carries an **issue type** (Epic/Story/Bug/Task/Sub-task/Improvement/Incident/Feature). | Extend | Task `type` → **Task Type** | Task Type fixtures | Selecting a type persists; type icon/label shows on card; no custom type field. | M | 1 |
| FR-TASK-009 | A card carries **Story Points**. | Extend | Task | Custom field `pulse_story_points` (Float), fixture | Points persist and feed velocity/burndown; blank allowed (treated as 0 in metrics). | M | 1 |
| FR-TASK-010 | A card carries a **Sprint** link. | Extend | Task | Custom field `pulse_sprint` (Link → Pulse Sprint), fixture | Setting sprint associates card with that sprint; only sprints of the same project selectable. | M | 1 |
| FR-TASK-011 | A card carries an **Epic** link. | Extend | Task | Custom field `pulse_epic` (Link → Task filtered to Type=Epic), fixture | Link accepts only Epic-type tasks; card groups under that epic in epic views. | S | 2 |
| FR-TASK-012 | A card carries a **Backlog Rank** for ordering. | Extend | Task | Custom field `pulse_rank` (Int), fixture, index | Rank persists; lower = higher; drives backlog/board ordering (§4, §6). | M | 1 |
| FR-TASK-013 | A card carries a **Release/Version** grouping. | Extend | Task | Custom field `pulse_release` (Data; Link if Release doctype added v2), fixture | Value persists and groups cards in release views/report. | C | 2 |
| FR-TASK-014 | Agile custom fields are grouped under a **Pulse** section/tab on the Task form. | Extend | Task | Custom field `pulse_section` (Section Break), fixture | Fields grouped; non-agile projects unaffected. | S | 1 |
| FR-TASK-015 | A card can be created quickly from the board/backlog with minimal fields. | Build | Task | SPA quick-add → whitelisted create API (standard doc API) | One-line entry creates a Task in the current column/backlog with rank appended. | M | 2 |
| FR-TASK-016 | A card can be deleted/cancelled per permissions. | Reuse | Task (delete / status Cancelled) | Core + Workflow `Cancelled` | Delete requires delete perm; Cancel is a workflow transition preserving history. | S | 1 |
| FR-TASK-017 | Bulk edit (assignee, sprint, status) on selected cards. | Reuse | Frappe list bulk actions | Core bulk edit / SPA multi-select | Selecting N cards and applying a change updates all; each fires normal validation. | C | 2 |
| FR-TASK-018 | A card exposes estimate-vs-actual (story points vs timesheet hours). | Build | Task + Timesheet | SPA rich-task pane + API | Card detail shows story points and summed actual hours from Timesheet (§10). | S | 2 |
| FR-TASK-019 | A card detail renders as a single rich pane (properties, sub-tasks, dependencies, activity, attachments). | Build | Task + related | SPA rich-task view + lean API | All facets load in one pane in ≤1s; edits save inline. | S | 2 |
| FR-TASK-020 | A lightweight **checklist** on a card (optional). | Build | Task sub-tasks (preferred) | Sub-tasks, or minimal child table only if justified | Checklist items track done/not-done; prefer sub-tasks before adding a child table. | C | 2 |

---

## 3. Story Points & Estimation

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-EST-001 | Story points are stored per card as a Float. | Extend | Task | Custom field `pulse_story_points` | Value 0–∞ persists; decimals allowed for teams using fractional points. | M | 1 |
| FR-EST-002 | Story points are editable inline on board/backlog cards. | Build | Task | SPA inline edit → doc API | Editing points on a card persists immediately with optimistic UI + reconcile. | S | 2 |
| FR-EST-003 | A sprint's **planned points** = sum of points of member cards at start. | Build | Pulse Sprint + Task | Computed field / server method | `planned_points` computed and stored read-only when sprint activates. | M | 1 |
| FR-EST-004 | A sprint's **completed points** = sum of points of cards reaching Done. | Build | Pulse Sprint + Status Log | Computed field / server method | `completed_points` reflects points of Done cards in the sprint. | M | 1 |
| FR-EST-005 | Story points snapshot is captured at each status change for burndown math. | Build | Pulse Task Status Log | `points_at_change` field, doc-event | Each Status Log row stores the card's points at the moment of transition. | M | 1 |
| FR-EST-006 | Estimation guidance (default scale) is documented; no forced scale enforced. | Reuse | — | Docs only | Teams may use any numeric scale; system does not reject non-Fibonacci values. | C | 1 |
| FR-EST-007 | Points roll up from sub-tasks to parent in views (display only). | Build | Task hierarchy | SPA aggregation | Parent card shows summed child points without overwriting its own field. | C | 2 |

---

## 4. Backlog

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-BKLG-001 | The backlog lists all cards of a project not yet Done, ordered by rank. | Build | Task | SPA backlog view + lean list API | List returns project's open tasks ordered by `pulse_rank` asc; paginated. | M | 2 |
| FR-BKLG-002 | Backlog uses core list in Phase 1 (sortable by rank) before the SPA. | Reuse | Frappe List View | List with sort on `pulse_rank` | Users can view/sort backlog in Desk list in Phase 1. | M | 1 |
| FR-BKLG-003 | Cards can be reordered in the backlog by drag-and-drop. | Build | Task | SPA DnD → rank update API | Dropping a card writes a new `pulse_rank`; order persists across reloads. | M | 2 |
| FR-BKLG-004 | Rank updates avoid full re-index (sparse/fractional or gap ranking). | Build | Task | Rank algorithm in API | A single move updates ≤2 rows; no O(n) rewrite; no rank collisions. | S | 2 |
| FR-BKLG-005 | A backlog card can be moved into a sprint. | Extend | Task | Set `pulse_sprint` via API / drag to sprint | Card's sprint link updates; it leaves backlog and appears in sprint scope. | M | 1 |
| FR-BKLG-006 | A card can be moved out of a sprint back to backlog. | Extend | Task | Clear `pulse_sprint` | Card returns to backlog ordering; metrics reflect scope change. | M | 1 |
| FR-BKLG-007 | Backlog supports filtering (type, assignee, priority, epic, label, text). | Build | Task | SPA filters → list API params | Applying filters narrows the list server-side; combinable; clearable. | S | 2 |
| FR-BKLG-008 | Backlog shows per-card points and a running selected-total when planning. | Build | Task | SPA aggregation | Selecting cards for a sprint shows summed points vs sprint capacity hint. | S | 2 |
| FR-BKLG-009 | Backlog groups by epic (optional). | Build | Task `pulse_epic` | SPA grouping | Toggling epic grouping clusters cards under their epic headers. | C | 2 |
| FR-BKLG-010 | Backlog quick-add appends a new card at the bottom with next rank. | Build | Task | SPA quick-add → create API | New card gets max(rank)+gap; appears at list end. | S | 2 |

---

## 5. Sprints

New doctype **Pulse Sprint**. One Active sprint per project (validated). Lifecycle: Planned → Active → Completed.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-SPR-001 | A user can create a **Pulse Sprint** (name, project, dates, goal). | Build | — | Pulse Sprint doctype | Sprint saves in Planned status linked to a Project. | M | 1 |
| FR-SPR-002 | Sprint auto-names as `SPR-{project}-{####}`. | Build | Frappe autoname | Doctype `autoname` format | Created sprints receive sequential, project-scoped names. | S | 1 |
| FR-SPR-003 | A sprint has a **goal** (short text). | Build | — | `goal` (Small Text) | Goal persists and shows in sprint header/board. | S | 1 |
| FR-SPR-004 | End date pre-fills from start date + default sprint length. | Build | Pulse Settings / Project | Client script / server default | Setting start date proposes end date = start + length; user can override. | S | 1 |
| FR-SPR-005 | A sprint can be **started/activated**. | Build | — | `status`→Active, `is_active`=1 | Activation stamps planned_points and start; sprint becomes the active board scope. | M | 1 |
| FR-SPR-006 | Only **one Active sprint per project** is allowed. | Build | — | `validate` on Pulse Sprint | Activating a second sprint while one is Active is rejected with a clear error. | M | 1 |
| FR-SPR-007 | Cards can be added to / removed from a sprint during planning. | Extend | Task | `pulse_sprint` link | Membership changes reflect immediately in sprint scope and metrics. | M | 1 |
| FR-SPR-008 | A sprint can be **closed/completed**, computing velocity. | Build | — | `status`→Completed, compute `velocity` | On close, `completed_points` and `velocity` are stamped read-only. | M | 1 |
| FR-SPR-009 | On close, incomplete cards are handled (spillover to backlog or next sprint). | Build | Task | Close dialog → bulk `pulse_sprint` update | User chooses move-to-next or return-to-backlog; unfinished cards updated accordingly. | S | 1 |
| FR-SPR-010 | `planned_points`, `completed_points`, `velocity` are read-only computed fields. | Build | — | Read-only fields + server compute | Fields are not user-editable; recomputed on activate/close. | M | 1 |
| FR-SPR-011 | Sprint dates validate (end ≥ start; warn on overlap with active sprint). | Build | — | `validate` | Invalid ranges rejected; overlapping active sprints warned. | S | 1 |
| FR-SPR-012 | A sprint report is available (planned vs completed, added/removed, spillover). | Build | Pulse Sprint + Status Log | Script report | Report lists committed vs done, scope changes, and carry-over per sprint. | S | 2 |
| FR-SPR-013 | Sprint list/board scoping: board defaults to the Active sprint for Scrum projects. | Build | Task + Pulse Sprint | SPA / Kanban filter | Opening a Scrum project's board shows the Active sprint's cards by default. | M | 1 |
| FR-SPR-014 | Sprint capacity hint from team availability (Holiday List). | Build | Holiday List | Computed capacity | Planning view shows working days × team as a soft capacity reference. | C | 2 |
| FR-SPR-015 | Notifications fire on sprint start and sprint close. | Reuse | Notification | Frappe Notification fixtures on Pulse Sprint | Members receive start/close notifications per their preferences. | S | 1 |

---

## 6. Board

Phase 1 reuses Frappe **Kanban Board**; Phase 2 delivers the SPA board. Columns come from **Pulse Task Workflow** states.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-BOARD-001 | Board columns are derived from **Pulse Task Workflow** states (Backlog, To Do, In Progress, In Review, Done, Cancelled). | Extend | Workflow / Workflow State | Workflow fixture; board reads `workflow_state` | Columns render exactly the workflow states, in defined order. | M | 1 |
| FR-BOARD-002 | Phase-1 board is a reused Frappe **Kanban Board** over Task. | Reuse | Kanban Board | Kanban Board fixture on Task | A working Kanban exists on install without custom UI code. | M | 1 |
| FR-BOARD-003 | Dragging a card between columns changes its workflow state. | Extend | Task workflow_state | Workflow transition via drag → doc API | Moving a card triggers the workflow transition and persists new state. | M | 1 |
| FR-BOARD-004 | Reaching **Done** sets Task `status=Completed` for core closure/costing. | Extend | Task `status` | Workflow field mapping / doc-event | A card in Done column has core status Completed; costing/closure logic runs. | M | 1 |
| FR-BOARD-005 | State transitions are gated by role. | Extend | Workflow Action / Role | Workflow transition rules | A role lacking a transition cannot perform that move; UI reflects allowed moves. | S | 1 |
| FR-BOARD-006 | Modern SPA board renders all columns and cards for a project/sprint. | Build | Task + Workflow | SPA board view + lean API | Board loads ≤1s for 500 cards; cards show key fields (title, type, points, assignee). | M | 2 |
| FR-BOARD-007 | SPA board supports drag-and-drop with optimistic UI and server reconcile. | Build | Task | SPA DnD → transition/rank API | Drag feels instant; a failed server write rolls the card back with a message. | M | 2 |
| FR-BOARD-008 | **Quick-add** a card directly into a column. | Build | Task | SPA quick-add → create API | Adding in a column creates a Task in that state with appended rank. | M | 2 |
| FR-BOARD-009 | Inline edit of card fields (assignee, points, priority) from the board. | Build | Task | SPA inline edit → doc API | Editing on the card persists without opening full detail. | S | 2 |
| FR-BOARD-010 | Within-column ordering persists via `pulse_rank`. | Extend | Task | `pulse_rank` update | Reordering cards in a column persists across reloads. | S | 2 |
| FR-BOARD-011 | **WIP limits** per column. | Build | — | SPA config (Pulse Settings/Project) + visual cap | Exceeding a column's WIP limit warns/blocks per configuration. | C | 2 |
| FR-BOARD-012 | **Swimlanes** (by assignee, epic, or priority). | Build | Task | SPA grouping | Selecting a swimlane dimension groups rows accordingly; toggleable. | C | 2 |
| FR-BOARD-013 | Board filter bar (assignee, type, epic, label, text). | Build | Task | SPA filters → API params | Filters narrow visible cards server-side; combinable; persist per session. | S | 2 |
| FR-BOARD-014 | Kanban-mode board (no sprint scope) for `pulse_board_type=Kanban` projects. | Extend | Task + Workflow | SPA / Kanban Board continuous mode | Kanban projects show a continuous board without sprint filtering. | S | 2 |
| FR-BOARD-015 | Card colour/badge by type and priority. | Build | Task Type / priority | SPA styling | Cards visually encode type and priority consistently. | C | 2 |

---

## 7. Epics & Hierarchy

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-EPIC-001 | An **Epic** is a Task of Task Type = Epic (no new hierarchy table). | Extend | Task Type | Task Type fixture `Epic` | Creating an Epic uses a normal Task with type Epic. | M | 1 |
| FR-EPIC-002 | Stories/tasks link to an epic via `pulse_epic`. | Extend | Task | Custom field `pulse_epic` (Link → Task, filtered Type=Epic) | Only Epic-type tasks are selectable; link persists. | S | 2 |
| FR-EPIC-003 | Sub-tasks nest under a parent via `parent_task`. | Reuse | Task `parent_task` | Core hierarchy | Parent shows its children; children show parent breadcrumb. | M | 1 |
| FR-EPIC-004 | An **epic view** lists epics with progress (child points done / total). | Build | Task | SPA epic view + API | Each epic shows child count and % points complete. | S | 2 |
| FR-EPIC-005 | Hierarchy display: Epic → Story → Sub-task in the rich task pane. | Build | Task hierarchy | SPA tree render | The pane shows the full ancestry/descendants of a card. | C | 2 |
| FR-EPIC-006 | Epic progress rolls up without duplicating child data. | Build | Task | SPA aggregation | Roll-up is computed on read; no denormalized copies stored on the epic. | S | 2 |

---

## 8. Dependencies

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-DEP-001 | A card can declare it **depends on** other tasks. | Reuse | Task `depends_on` (Task Depends On) | Core child table | Adding a dependency persists; no new dependency doctype created. | M | 1 |
| FR-DEP-002 | Dependencies are visible on the card detail. | Reuse / Build | Task `depends_on` | Desk (P1) / SPA pane (P2) | Depends-on list shows linked tasks with status. | S | 1 |
| FR-DEP-003 | A card blocked by an incomplete dependency is visually flagged. | Build | Task `depends_on` | SPA indicator | Cards with unresolved dependencies show a "blocked" badge. | C | 2 |
| FR-DEP-004 | Dependency completion can gate a transition (optional, workflow-aware). | Extend | Workflow + `depends_on` | `validate`/workflow condition | Configurable rule warns/blocks moving a card whose dependencies aren't Done. | C | 2 |
| FR-DEP-005 | Dependencies render on Gantt/timeline. | Reuse | Frappe Gantt | Core Gantt view | Gantt shows dependency links from core `depends_on`. | C | 2 |

---

## 9. Milestones & Releases

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-MILE-001 | A milestone is a Task flagged **is_milestone**. | Reuse | Task `is_milestone` | Core field | Marking is_milestone identifies the task as a milestone in views. | S | 1 |
| FR-MILE-002 | Milestones appear distinctly on timeline/roadmap. | Build | Task `is_milestone` | SPA roadmap marker | Milestones render as diamond markers on the timeline. | C | 3 |
| FR-MILE-003 | Project-level status milestones can use **Project Update**. | Reuse | Project Update | Core doctype | Project health checkpoints recorded via Project Update. | C | 2 |
| FR-REL-001 | A card carries a **Release/Version** value. | Extend | Task | Custom field `pulse_release` (Data; Link if Release doctype v2) | Value persists and groups cards by release. | C | 2 |
| FR-REL-002 | A **release view** groups cards by release with completion status. | Build | Task | SPA release view + API | Each release lists its cards and % done. | C | 3 |
| FR-REL-003 | A **release report** summarizes scope and completion per release. | Build | Task | Script/Query report | Report shows planned vs done items per release value. | C | 3 |
| FR-REL-004 | *(Phase note)* A dedicated **Pulse Release** doctype may replace the Data field in v2/v3 if grouping needs metadata; requires canonical-model update first. | Build | — | New doctype (gated) | Not built unless canonical §3 is amended; documented as a phase note. | W | 3 |

---

## 10. Assignment & Role Hierarchy

Assignment reuses **ToDo / `_assign`**. Hierarchy adds an *assign-down-only* constraint enforced server-side.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-ASGN-001 | A card can be assigned to one or more users. | Reuse | ToDo / `_assign` | Core assignment | Assignees persist on `_assign`; assignment notifications fire. | M | 1 |
| FR-ASGN-002 | Assignees are visible as avatars on cards. | Build / Reuse | `_assign` | Kanban (P1) / SPA (P2) | Card shows assignee avatars sourced from `_assign`. | M | 1 |
| FR-ASGN-003 | A user may assign work only to users of **equal or lower rank**. | Extend | Role / Has Role | `validate`/assignment hook + Pulse Role Rank map | Assigning up the hierarchy is rejected server-side with a clear message. | M | 1 |
| FR-ASGN-004 | Role ranks are data-driven via **Pulse Role Rank** in Pulse Settings. | Build | — | Pulse Role Rank child table | Editing a role's rank changes assignment eligibility without code change. | M | 1 |
| FR-ASGN-005 | Default ranks ship as fixtures (Admin 100 … Viewer 0). | Extend | Role | Fixture (Pulse Settings + Role Rank) | Fresh install has the seven Pulse roles ranked per canonical §6. | M | 1 |
| FR-ASGN-006 | A user's effective rank = max rank across their roles. | Extend | Has Role | Server computation | A user with multiple roles is evaluated at their highest rank. | M | 1 |
| FR-ASGN-007 | Hierarchy enforcement is server-side, never UI-only. | Extend | — | `validate` + optional `permission_query_conditions` | Bypassing the UI (direct API) still rejects up-assignment. | M | 1 |
| FR-ASGN-008 | Hierarchical assignment can be globally toggled. | Build | Pulse Settings | `enable_hierarchical_assignment` (Check) | Disabling the toggle relaxes to standard Frappe assignment. | S | 1 |
| FR-ASGN-009 | The assignee picker in the SPA shows only eligible (assignable) users. | Build | `_assign` + rank map | SPA + eligibility API | Picker lists only equal/lower-rank users; server still re-validates. | S | 2 |
| FR-ASGN-010 | Assignment changes are auditable. | Reuse | Version / Activity Timeline | Core | Each assignment change is recorded in the Task timeline. | S | 1 |
| FR-ASGN-011 | Seven Pulse roles ship as fixtures. | Extend | Role | Role fixtures | Pulse Admin/Manager/Team Lead/Senior/Junior/Intern/Viewer exist on install. | M | 1 |

---

## 11. Timesheet Integration

Actual effort comes from **Timesheet** — never hand-entered.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-TIME-001 | Actual hours on a card derive from **Timesheet Detail** rows linked to the task. | Reuse | Timesheet / Timesheet Detail | Core aggregation | Card actuals = sum of timesheet hours for that task; no manual actual field. | M | 1 |
| FR-TIME-002 | A user can log time against a card. | Reuse | Timesheet | Core form / SPA "Log time" → Timesheet API | Logging time creates a Timesheet Detail against the task; hours roll up. | S | 2 |
| FR-TIME-003 | Timesheet hours roll up to Project costing/billing unchanged. | Reuse | Timesheet + Project | Core | Costing/billing on the Project reflects logged hours exactly as core does. | M | 1 |
| FR-TIME-004 | Billing/costing rates come from **Activity Type / Activity Cost**. | Reuse | Activity Type / Activity Cost | Core | Rates apply automatically to logged time per core rules. | S | 1 |
| FR-TIME-005 | The rich task pane shows estimate (points) vs actual (hours) side by side. | Build | Task + Timesheet | SPA + API | Pane displays story points and total actual hours together. | S | 2 |
| FR-TIME-006 | Sprint-level actual hours aggregate from member cards' timesheets. | Build | Timesheet + Pulse Sprint | Report/API aggregation | Sprint report can show total actual hours for the sprint's cards. | C | 2 |

---

## 12. Metrics & Reports

Built on the reporting engine (Script/Query Report + Dashboard Chart + Number Card). Point metrics use Status Log; hour metrics use Timesheet.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-MET-001 | **Velocity** — completed points per sprint. | Build | Pulse Sprint | Script/Query report + Dashboard Chart | Chart shows completed points across recent sprints. | M | 1 |
| FR-MET-002 | **Burndown** — remaining points vs day over the sprint. | Build | Pulse Task Status Log + Pulse Sprint | Script report + chart | Curve computed from status transitions and sprint dates/working days. | M | 1 |
| FR-MET-003 | **Burnup** — scope vs completed over time. | Build | Status Log + Sprint | Script report + chart | Shows total scope line and completed line; scope changes visible. | S | 2 |
| FR-MET-004 | **Cumulative Flow Diagram** — count per state per day. | Build | Pulse Task Status Log | Script report + chart | Stacked area of card counts per workflow state per day. | S | 2 |
| FR-MET-005 | **Cycle Time** — time from In Progress to Done. | Build | Pulse Task Status Log | Script report | Per-card and average cycle time computed from timestamps. | S | 2 |
| FR-MET-006 | **Lead Time** — time from creation/Backlog to Done. | Build | Pulse Task Status Log | Script report | Per-card and average lead time computed from timestamps. | S | 2 |
| FR-MET-007 | **Workload** — open points per assignee. | Build | `_assign` + Task points | Script report + chart | Report sums open points grouped by assignee. | S | 2 |
| FR-MET-008 | **Sprint Report** — planned vs completed, added/removed, spillover. | Build | Pulse Sprint + Status Log | Script report | Report reconciles committed scope, completions, and carry-over. | S | 2 |
| FR-MET-009 | Heavy metrics precomputed on a schedule, not per page load. | Build | Scheduler / Dashboard Chart cache | Scheduled job → cache/summary | Burndown snapshot job runs daily; charts read cached values. | S | 2 |
| FR-MET-010 | Metrics respect project/user permissions. | Reuse | Report + permissions | Core report permissions | A user sees metrics only for projects they can access. | M | 1 |
| FR-MET-011 | Key metrics surface as **Number Cards** on the Pulse workspace. | Build | Number Card | Fixture | Workspace shows velocity/open-points cards. | C | 2 |
| FR-MET-012 | All point metrics treat blank story points as 0 consistently. | Build | — | Report logic | No metric errors on unpointed cards; they contribute 0. | S | 1 |

---

## 13. Notifications

Reuse Frappe **Notification** entirely.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-NOTIF-001 | Assignment notifies the assignee. | Reuse | ToDo / Notification | Core assignment notification | Assignee receives notification per their settings. | M | 1 |
| FR-NOTIF-002 | Comment/mention notifies participants. | Reuse | Communication / Notification | Core | Mentioned/participating users are notified. | M | 1 |
| FR-NOTIF-003 | Sprint start/close notifies sprint members. | Reuse | Notification | Notification fixture on Pulse Sprint | Members receive start/close alerts. | S | 1 |
| FR-NOTIF-004 | Status change to a watched card notifies watchers. | Reuse | Notification | Notification fixture on Task workflow_state | Watchers notified on transitions per rule. | C | 2 |
| FR-NOTIF-005 | Notification channels/toggles honour **Pulse Settings** + Notification Settings. | Extend | Notification Settings | Pulse Settings `email_notifications`/`desktop_notifications` | Disabling a channel suppresses those notifications. | S | 1 |
| FR-NOTIF-006 | Due-date/overdue reminders use Frappe Notification (no destructive status write). | Reuse | Notification | Scheduled Notification | Overdue cards trigger a reminder; status is never auto-overwritten. | S | 1 |

---

## 14. Search & Filters / Saved Views

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-SRCH-001 | Global search finds tasks/projects/sprints. | Reuse | Frappe Global Search | Core search | Searching a term returns matching Tasks/Projects/Sprints. | S | 1 |
| FR-SRCH-002 | Board/backlog filter by type, assignee, priority, epic, label, text. | Build | Task | SPA filters → list API | Combinable filters narrow results server-side. | M | 2 |
| FR-SRCH-003 | Filters persist per user/session. | Build | — | SPA local/user pref | Reopening a view restores the last filter set. | C | 2 |
| FR-SRCH-004 | **Saved views** (named filter+sort presets). | Build | — | SPA saved view (user pref / light store) | A user can save, name, and re-apply a view. | C | 2 |
| FR-SRCH-005 | Phase-1 filtering via core List View filters. | Reuse | Frappe List View | Core filters | Users filter tasks in Desk lists before the SPA exists. | M | 1 |
| FR-SRCH-006 | Tags/labels reuse `_user_tags` / **Tag** (no Pulse Label doctype). | Extend | Tag / `_user_tags` | Core tagging | Adding a tag persists and is filterable; no custom label table. | S | 1 |

---

## 15. Settings

New Single **Pulse Settings** + child **Pulse Role Rank**.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-SET-001 | **Pulse Settings** single holds app configuration. | Build | — | Single doctype | Settings page saves and is readable by the app. | M | 1 |
| FR-SET-002 | **Default sprint length (days)** configurable (default 14). | Build | — | `default_sprint_length_days` (Int) | New projects/sprints inherit this default. | M | 1 |
| FR-SET-003 | **Default board type** configurable (Scrum/Kanban, default Scrum). | Build | — | `default_board_type` (Select) | New projects default to this board type. | S | 1 |
| FR-SET-004 | **Hierarchical assignment** toggle (default on). | Build | — | `enable_hierarchical_assignment` (Check) | Toggle governs FR-ASGN-003 enforcement. | M | 1 |
| FR-SET-005 | Notification toggles (email, desktop). | Build | — | `email_notifications`, `desktop_notifications` (Check) | Toggles gate FR-NOTIF-005. | S | 1 |
| FR-SET-006 | **Role ranks** table drives hierarchy. | Build | — | `role_ranks` → Pulse Role Rank | Editing ranks changes assignment eligibility. | M | 1 |
| FR-SET-007 | **Working-days source** (Holiday List) for burndown. | Build | Holiday List | `working_days_source` (Link) | Burndown excludes non-working days per this list. | S | 2 |
| FR-SET-008 | Obsolete legacy Pulse Settings fields are dropped/migrated. | Extend | — | Migration / fixture | Post-migration, only canonical fields remain. | M | 1 |
| FR-SET-009 | Settings editable only by Pulse Admin / System Manager. | Reuse | DocPerm | Permission on Pulse Settings | Non-admins cannot change global settings. | M | 1 |

---

## 16. Calendar / Gantt / Timeline

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-CAL-001 | Tasks appear in the Frappe **Calendar** view by due date. | Reuse | Frappe Calendar | Core view | Tasks with dates render on the calendar. | S | 1 |
| FR-CAL-002 | Tasks and dependencies render in the Frappe **Gantt** view. | Reuse | Frappe Gantt | Core view | Gantt shows tasks, dates, and `depends_on` links. | S | 1 |
| FR-CAL-003 | A **Roadmap/Timeline** SPA view spans epics/releases over time. | Build | Task + dates | SPA timeline view | Timeline shows epics/releases with bars and milestones. | C | 3 |
| FR-CAL-004 | Timeline ranges lazy-load / virtualize for performance. | Build | — | SPA virtualization | Large date ranges scroll smoothly without loading everything. | C | 3 |

---

## 17. Status History (foundational for metrics)

New append-only **Pulse Task Status Log**, written by a doc-event; underpins §12.

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-LOG-001 | Every workflow_state/status change on a Task writes a **Pulse Task Status Log** row. | Build | Task doc-event | `on_update` doc-event → Pulse Task Status Log | A transition produces exactly one log row with from/to/timestamp. | M | 1 |
| FR-LOG-002 | The log records task, project, sprint, from_state, to_state, changed_by, changed_on, points_at_change. | Build | — | Doctype fields | All fields populated correctly per transition. | M | 1 |
| FR-LOG-003 | The log is append-only — never edited or deleted by users. | Build | — | Read-only perms / permlevel | Users cannot modify existing log rows. | M | 1 |
| FR-LOG-004 | Log rows are indexed on task, project, sprint, changed_on. | Build | — | Doctype indexes | Metric queries filtering by these are index-backed. | M | 1 |
| FR-LOG-005 | The doc-event is idempotent (no duplicate rows for a no-op save). | Build | — | Change-detection in hook | Saving a Task without a state change writes no log row. | S | 1 |

---

## 18. Platform, Migration & Non-Functional-Adjacent Functional Requirements

| ID | Requirement | R/E/B | Reused component | Mechanism | Acceptance criteria | Pri | Ph |
|---|---|---|---|---|---|---|---|
| FR-PLAT-001 | Clean install via `bench install-app pulse` ships all fixtures. | Extend | Fixtures | Fixture export | Fresh install yields custom fields, roles, workflow, task types, settings, workspace with no manual steps. | M | 1 |
| FR-PLAT-002 | Install is idempotent (safe re-run). | Extend | — | Guarded install hooks | Re-running install/migrate does not duplicate fixtures. | M | 1 |
| FR-PLAT-003 | No core ERPNext/Frappe files are edited; all additions via module/fixtures. | Extend | — | Module + fixtures | Grep confirms zero edits to erpnext/frappe core; upgrade-safe. | M | 1 |
| FR-PLAT-004 | A **Pulse workspace** ties board/backlog/sprints/reports together in Desk. | Build | Workspace | Workspace fixture | Workspace loads with working shortcuts (no broken links). | M | 1 |
| FR-PLAT-005 | Whitelisted APIs live under `pulse.api.*` and are thin. | Build | `@frappe.whitelist` | Whitelisted endpoints | Endpoints return lean payloads; writes go through standard document API. | M | 2 |
| FR-PLAT-006 | No blanket `ignore_permissions=True` on user paths. | Reuse | Frappe permissions | Standard doc API | All writes enforce roles/permissions automatically. | M | 1 |
| FR-PLAT-007 | Board API returns lean, paginated, server-filtered payloads. | Build | `get_list` | Whitelisted API with field pruning | 500-card board payload loads ≤1s; no N+1. | S | 2 |
| FR-PLAT-008 | Legacy Pulse* doctype data migrates into core Task/Project + new doctypes. | Build | — | One-time migration script | Documented migration maps old records to core with no data loss. | S | 1 |
| FR-PLAT-009 | Phase-2 SPA served at route `/pulse` (Gameplan/Helpdesk pattern). | Build | frappe-ui | Vue 3 SPA | `/pulse` loads the SPA; Desk remains available for finance/ops. | S | 2 |
| FR-PLAT-010 | App title is **Pulse**; module is **Pulse**; no "PMO"/"Project Management Office" strings. | Extend | — | Config/rename | Grep finds no legacy naming; UI shows "Pulse" everywhere. | M | 1 |

---

## Traceability & governance notes

- Every requirement maps to canonical `_canonical-model.md` sections: Projects/Tasks fields → §4; workflow/board → §5; roles/hierarchy → §6; Task Types → §7; reports → §8; new doctypes → §3; phases → §10.
- The **reuse gate** applies to any change: a new requirement must first be checked against ERPNext/Frappe (Reuse), then Extend, and only then Build. New doctypes beyond the four canonical ones (e.g. Pulse Release, FR-REL-004) require amending the canonical model first — hence tagged `Won't` for this release.
- Actual-effort requirements (§11) always source from **Timesheet**; there is no hand-entered actuals field, by design.
- Point-based metrics (§12) always source from **Pulse Task Status Log** (§17); the log is therefore a Phase-1 must even though most metrics that consume it land in Phase 2.

*End of Document 4 — Functional Requirements.*
