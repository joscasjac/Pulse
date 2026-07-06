# Pulse — Product Requirements Document

**Document 2 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. Product Vision

> **Pulse makes ERPNext feel like Jira and Plane — while every hour, cost, and invoice still lives in ERPNext.**

A delivery team plans a sprint, drags cards across a board, watches a burndown, and reviews a roadmap in a fast, modern UI. Behind the glass, **each card is an ERPNext Task, each logged hour is an ERPNext Timesheet line, each project is an ERPNext Project** with real costing and billing. There is one source of truth and two experiences on top of it: the classic ERPNext Desk for finance/ops, and Pulse for delivery teams.

The product exists to eliminate the tool-sprawl split between "where we deliver" (Jira/Plane) and "where finance lives" (ERPNext), by giving teams a reason to work *inside* ERPNext — improving data quality upstream of billing while giving them Jira-grade agile and Plane-grade UX.

---

## 2. Personas

Each persona maps to a Pulse role fixture (`_canonical-model.md §6`). Ranks (Admin 100 → Manager 80 → Team Lead 60 → Senior Dev 40 → Junior Dev 20 → Intern 10 → Viewer 0) govern hierarchical assignment.

### P1 — Pulse Admin (rank 100)
- **Who:** Platform owner / ERPNext administrator.
- **Goals:** Install and configure Pulse; set default sprint length, board type, role ranks, workflow; ship fixtures; keep upgrades safe.
- **Pains:** Custom code that breaks on ERPNext upgrade; parallel data models that don't roll up to finance; permission bypasses that leak data.
- **Success:** Clean install, no core edits, everything configurable via Pulse Settings.

### P2 — Pulse Manager / Project Manager (rank 80)
- **Who:** Delivery/project manager accountable for scope, schedule, margin.
- **Goals:** Plan and close sprints; triage and order the backlog; assign work down the hierarchy; review velocity and burndown; ensure timesheets feed billing.
- **Pains:** Delivery data trapped in Jira/Plane, disconnected from ERPNext costing; no velocity/burndown in ERPNext; manual status roll-ups.
- **Success:** Runs a whole sprint on core Task data; sees accurate burndown and margin in one system.

### P3 — Team Lead (rank 60)
- **Who:** Leads a squad's daily execution.
- **Goals:** Run the board; assign stories to developers; manage sprint scope and WIP; unblock dependencies.
- **Pains:** Slow, dense Task views; no quick-add or inline edit; no board scoped to the active sprint.
- **Success:** Fast board, ≤ 2 clicks to move/assign a card, sprint-scoped columns.

### P4 — Senior Developer (rank 40)
- **Who:** Owns stories, mentors juniors.
- **Goals:** Estimate story points; break stories into sub-tasks; assign sub-tasks down; move cards through workflow; log time.
- **Pains:** Estimation not first-class; sub-task hierarchy clunky in Desk.
- **Success:** Points on cards, sub-tasks via `parent_task`, assign-down works, actuals from Timesheet.

### P5 — Junior Developer (rank 20)
- **Who:** Executes assigned work.
- **Goals:** See "my cards"; update status; log time; comment; attach files.
- **Pains:** Being expected to assign up the chain; unclear what's mine this sprint.
- **Success:** Clear personal board; cannot mistakenly assign above their rank.

### P6 — Intern (rank 10)
- **Who:** Learning; limited scope.
- **Goals:** Work a small set of assigned cards under supervision.
- **Pains:** Overwhelm; accidental broad edits.
- **Success:** Narrow, safe surface; assign-up blocked server-side.

### P7 — Viewer / Stakeholder (rank 0)
- **Who:** Internal observer (e.g. exec, PMO analyst).
- **Goals:** Read boards, roadmaps, sprint reports; no edits.
- **Pains:** Being given edit access they shouldn't have.
- **Success:** Read-only, accurate views.

### P8 — Finance / Client Stakeholder (ERPNext roles)
- **Who:** Finance controller or external client sponsor.
- **Goals:** Trust that delivery effort rolls into costing/billing; consume margin, invoices, timesheet totals in ERPNext Desk.
- **Pains:** Delivery activity that never reaches finance; hand-entered hours that don't match reality.
- **Success:** Every Pulse card's time and cost appears in ERPNext automatically; financial fields protected from delivery-user edits (via `permlevel`).

---

## 3. Key User Journeys

### J1 — Plan a sprint (Pulse Manager)
1. Open project with `pulse_enable_scrum = 1`. 2. Create **Pulse Sprint** (name, dates, goal). 3. Open Backlog (Tasks ordered by `pulse_rank`). 4. Estimate story points on candidate Tasks. 5. Drag/assign Tasks into the sprint (`pulse_sprint` link set). 6. Mark sprint **Active** (only one Active sprint/project). 7. `planned_points` computed.

### J2 — Run a sprint (Team Lead / Developers)
1. Open sprint-scoped board (columns = workflow states). 2. Drag a card Backlog → To Do → In Progress → In Review → Done. 3. Each move writes a **Pulse Task Status Log** row (doc-event). 4. Developers log time via **Timesheet**; actuals roll to Project. 5. Burndown updates from Status Log.

### J3 — Triage the backlog (Manager / Team Lead)
1. Open Backlog view. 2. Reorder cards (`pulse_rank`). 3. Set Task Type (Epic/Story/Bug/…), priority, epic link. 4. Move ready cards into the active/next sprint or leave in Backlog state.

### J4 — Assign down the hierarchy (any assigner)
1. Open a card. 2. Add assignee via standard `_assign`. 3. Server-side `validate` checks assigner's max rank ≥ assignee's max rank. 4. Assign-up is rejected with a clear message; assign-down/sideways succeeds.

### J5 — Log time (Developer)
1. From a card, create/associate a **Timesheet Detail** (Activity Type, hours). 2. Timesheet submitted → actual effort & cost roll into the Task's Project. 3. No hand-entered "actual hours" field on the card.

### J6 — Review burndown & velocity (Manager)
1. Open the sprint dashboard. 2. **Burndown** chart: remaining points vs day (Status Log + sprint dates + working days). 3. Close sprint → `completed_points` and `velocity` computed. 4. **Velocity** chart across sprints informs next-sprint capacity.

---

## 4. Feature List (MoSCoW × Phase)

Priority: **M**ust / **S**hould / **C**ould / **W**on't (this release). Phase per `_canonical-model.md §10`.

| # | Feature | MoSCoW | Phase |
|---|---|---|---|
| F1 | Card = ERPNext Task (custom fields, no parallel table) | M | 1 |
| F2 | Project = ERPNext Project (+ agile custom fields, opt-in scrum) | M | 1 |
| F3 | Task Type fixtures (Epic/Story/Bug/Task/Sub-task/Improvement/Incident/Feature) | M | 1 |
| F4 | Pulse Task Workflow (Backlog→To Do→In Progress→In Review→Done, +Cancelled) | M | 1 |
| F5 | Pulse Sprint doctype + lifecycle (Planned/Active/Completed) | M | 1 |
| F6 | One Active sprint per project (validated) | M | 1 |
| F7 | Story points (`pulse_story_points`) | M | 1 |
| F8 | Backlog view + ordering (`pulse_rank`) | M | 1 |
| F9 | Pulse Task Status Log (append-only, doc-event) | M | 1 |
| F10 | Kanban board (reuse Frappe Kanban Board) | M | 1 |
| F11 | Assignment via `_assign` (reuse) | M | 1 |
| F12 | Hierarchical assignment enforcement (role ranks) | M | 1 |
| F13 | Actual effort from Timesheet (reuse) | M | 1 |
| F14 | Velocity report + chart | M | 1 |
| F15 | Burndown report + chart | M | 1 |
| F16 | Pulse Settings (single) + Pulse Role Rank | M | 1 |
| F17 | Pulse roles fixtures | M | 1 |
| F18 | Desk Pulse workspace | M | 1 |
| F19 | Epic linking (`pulse_epic`, Task Type = Epic) | S | 1 |
| F20 | Release/version grouping (`pulse_release`) | S | 1 |
| F21 | Comments / attachments / notifications on cards (reuse) | M | 1 |
| F22 | One-time migration Pulse*→core | M | 1 |
| F23 | frappe-ui SPA: Board/Backlog/Sprint/Rich Task | M | 2 |
| F24 | Burnup, CFD, Cycle/Lead time reports | S | 2 |
| F25 | WIP limits + swimlanes | S | 2 |
| F26 | Saved filters / views | C | 2 |
| F27 | Epics view (SPA) | S | 2 |
| F28 | Roadmap / Timeline views | S | 3 |
| F29 | Modules & Cycles (Plane-style) | C | 3 |
| F30 | Releases + release report (doctype) | C | 3 |
| F31 | Pages/Docs per project | C | 3 |
| F32 | Automations UI (reuse Notification/Assignment Rule/Auto-repeat) | C | 3 |
| F33 | Plugin/extension API + hooks surface | C | 3 |
| F34 | Mobile / PWA | W (this release) | 3 |
| F35 | Custom auth / parallel work-item table | W (never) | — |

---

## 5. Epics → User Stories with Acceptance Criteria (MVP)

Acceptance criteria use Given/When/Then. Scope = Phase-1 MVP.

### EPIC A — Reuse-First Foundation

**A1 — As a Pulse Admin, I want Pulse to install cleanly so the app is usable out of the box.**
- Given a Frappe v16.25 / ERPNext v16.26 bench, When I run `bench install-app pulse`, Then install completes with no FileNotFoundError and fixtures (custom fields, roles, Task Types, workflow, Pulse Settings) are created.
- Given a fresh install, When I open the Pulse workspace, Then it renders (no 404/blank flagship page).

**A2 — As a Pulse Admin, I want agile to be opt-in per project.**
- Given a Project, When I set `pulse_enable_scrum = 1`, Then agile fields/views activate for that project; When it is 0, Then the project behaves as classic ERPNext.

### EPIC B — Work Items on Core Task

**B1 — As a Senior Developer, I want to estimate a card in story points.**
- Given a Task, When I set `pulse_story_points`, Then the value persists on the Task and feeds sprint/velocity math.

**B2 — As a Team Lead, I want issue types on cards.**
- Given a Task, When I set `type` to a Pulse Task Type (Epic/Story/Bug/…), Then the card renders with the corresponding type; no custom type field is introduced.

**B3 — As a Manager, I want epics to group stories.**
- Given a Task with Task Type = Epic, When I link child Tasks via `pulse_epic`, Then those Tasks are grouped under the epic in views.

### EPIC C — Sprint Lifecycle

**C1 — As a Manager, I want to create and activate a sprint.**
- Given a scrum-enabled Project, When I create a Pulse Sprint and set status Active, Then it becomes the project's Active sprint.
- Given a project already has an Active sprint, When I try to activate a second, Then validation blocks it with a clear message ("one active sprint per project").

**C2 — As a Manager, I want to add tasks to a sprint.**
- Given a Task and an active/planned sprint in the same project, When I set `pulse_sprint`, Then the Task is scoped to that sprint and counts toward `planned_points`.

**C3 — As a Manager, I want to close a sprint and capture velocity.**
- Given an Active sprint, When I set status Completed, Then `completed_points` and `velocity` are computed and read-only, and incomplete tasks are handled per spillover rules (defined in Sprint doc).

### EPIC D — Board & Status History

**D1 — As a Team Lead, I want a Kanban board whose columns are workflow states.**
- Given scrum-enabled Tasks, When I open the board, Then columns render from Pulse Task Workflow states (Backlog/To Do/In Progress/In Review/Done).

**D2 — As a Developer, I want to move a card and have it recorded.**
- Given a card, When I move it between columns, Then Task `workflow_state` updates AND one Pulse Task Status Log row is appended (`from_state`, `to_state`, `changed_by`, `changed_on`, `points_at_change`).
- Given a card reaches Done, Then Task `status` is set to Completed via workflow mapping so core costing/closure works.
- Given any user, When they attempt to edit/delete a Status Log row, Then it is denied (append-only, permlevel/read-only).

### EPIC E — Backlog

**E1 — As a Manager, I want an ordered backlog.**
- Given un-sprinted Tasks, When I reorder them, Then `pulse_rank` persists (lower = higher) and the order is stable across reloads.

**E2 — As a Manager, I want to move backlog items into a sprint.**
- Given a backlog Task, When I move it to a sprint, Then `pulse_sprint` is set and it leaves the backlog view.

### EPIC F — Assignment & Hierarchy

**F1 — As any user, I want to assign a card via standard assignment.**
- Given a card, When I assign a user via `_assign`, Then the standard ToDo/assignment machinery fires (notification, "assigned to me").

**F2 — As the system, I want to enforce assign-down-only.**
- Given assigner with max rank R and assignee with max rank A, When A ≤ R, Then assignment succeeds; When A > R, Then it is rejected server-side with a clear message. Enforcement is in `validate`/assignment hook, never UI-only.

### EPIC G — Time & Financials

**G1 — As a Developer, I want actual effort to come from Timesheet.**
- Given a card, When I log time via Timesheet Detail, Then actual hours/cost roll into the Task's Project; no hand-entered actual-hours field exists on the card.

**G2 — As Finance, I want financial fields protected.**
- Given a delivery user, When they open a card/project, Then financial/costing fields are read-only to them (protected via `permlevel`).

### EPIC H — Metrics

**H1 — As a Manager, I want a burndown for the active sprint.**
- Given an Active sprint with status history, When I open the burndown, Then it shows remaining points per day using Status Log + sprint dates + working days (Holiday List).

**H2 — As a Manager, I want velocity across sprints.**
- Given ≥ 1 completed sprint, When I open velocity, Then it shows completed points per sprint.

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Board loads < 1s for 500 tasks; lean board API payloads (field pruning); common actions ≤ 2 clicks; debounced drag persistence with optimistic UI; burndown snapshotted (scheduler), not recomputed per render. |
| **Scalability** | Thousands of tasks/project, hundreds of sprints; indexed queries on Task `status`/`workflow_state`, `project`, `pulse_sprint`, `pulse_rank`; cursor/limit pagination; heavy metrics precomputed to Dashboard Chart cache / summary. |
| **Security** | Reuse Frappe auth/session/CSRF (no custom auth); RBAC via roles + `permlevel`; hierarchical assignment enforced server-side; whitelist minimally and validate every argument; **no blanket `ignore_permissions=True`**; financial fields protected by `permlevel`; every endpoint checks `frappe.has_permission`. |
| **Usability** | Jira/Plane muscle memory (drag, quick-add, inline edit, command-k in SPA); progressive disclosure (agile hidden until scrum enabled); frappe-ui components; keyboard nav, contrast, ARIA on board elements. |
| **Upgrade-safety** | All additions via fixtures/custom fields/dedicated Pulse module; **zero core-file edits, no monkey-patching**; idempotent installs/migrations; CI against target Frappe/ERPNext versions. |
| **Reliability** | Append-only Status Log for clean metric math; no destructive scheduled status writes; idempotent doc-events. |
| **Maintainability** | ≥ 70% reuse/extension; thin controllers; test the extensions, not the framework; versioned `pulse.api.*`. |

---

## 7. KPIs / Success Metrics

| KPI | Target |
|---|---|
| Sprint runnable end-to-end on core Task data | Yes (MVP acceptance gate) |
| Board load time (500 tasks) | < 1 second |
| Clicks for common card actions | ≤ 2 |
| Financial roll-up correctness | 100% of Pulse tasks roll to Project costing/billing |
| Reuse ratio (features via reuse/extension) | ≥ 70% (measured in Reuse Matrix, Doc 5) |
| Core-file edits | 0 |
| Hierarchical assignment violations reaching persistence | 0 (blocked server-side) |
| Metric reproducibility | Burndown/velocity reproducible from Status Log |
| Time-to-value | Clean install → first sprint planned within one session |
| Adoption | Delivery teams working inside ERPNext (timesheet completeness ↑) |

---

*End of Document 2. Proceed to Document 3 — Business Requirements.*
