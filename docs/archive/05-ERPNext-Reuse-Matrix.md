# Pulse — ERPNext Reuse Matrix

**Document 5 of 21 · The Reuse Contract**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe **v16.25** · ERPNext **v16.26**
**Module:** Pulse · **App:** pulse
**Governing rule:** **Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).**
**Status:** Normative. This document is the contract; it conforms to `_canonical-model.md` (the single source of truth) and `00-Pulse-Enterprise-Analysis.md`. Where any downstream document or PR disagrees with this matrix, this matrix wins until the canonical model is updated first.

---

## 1. Purpose — why this document exists and how to use it

The single largest defect in the current Pulse build was **re-cloning ERPNext**: ~10 parallel `Pulse *` doctypes (`Pulse Project`, `Pulse Task`, `Pulse Team`, `Pulse Milestone`, …) that duplicated a project engine ERPNext already ships. The consequence was total: data entered in Pulse never reached ERPNext costing/billing/timesheets, and none of Frappe's assignment, permission, notification, report, and audit machinery applied automatically. Every feature had to be hand-built — and hand-maintained.

This matrix is the **antidote and the gate**. It enumerates *every* project-management capability Pulse must offer and assigns each to exactly one of three buckets:

- **REUSE** — ERPNext/Frappe already does this. Use it as-is. Write no code.
- **EXTEND** — ERPNext almost does this. Add a custom field, a workflow, a fixture, a doc-event, or a permission hook. Change data/config, not the data model.
- **BUILD** — ERPNext has *no equivalent*. Create the (deliberately tiny) new surface: 4 new doctypes, the SPA, and metric reports — all still sitting *on top of* core Task/Project.

### 1.1 The reuse-first hierarchy (apply in order)

```
1. REUSE   → Does ERPNext/Frappe already do this?           → use it, ship nothing.
2. EXTEND  → Does it almost do this?                        → custom field / workflow / fixture / hook.
3. BUILD   → Is there genuinely no equivalent?              → new doctype / SPA view / report (still over core).
```

You may only descend a level when the level above genuinely cannot serve the need. "Almost works but the UX is dated" is **EXTEND or a front-end BUILD over the same data** — never a new back-end table.

### 1.2 How to use this as a PR gate

Every pull request that adds a doctype, field, table, endpoint, or model concept **must** answer, in the PR description, the two gate questions:

> **Gate Q1 — "Does ERPNext already do this?"** If yes → REUSE. Reject the new code.
> **Gate Q2 — "Can we extend instead of build?"** If yes → EXTEND (custom field / workflow / fixture / doc-event / permission hook). Reject the new table.

A new **doctype** is admissible only if it is one of the four sanctioned in §5 (**Pulse Sprint, Pulse Task Status Log, Pulse Settings, Pulse Role Rank**) — *any* other new doctype fails the gate by definition and must be justified by first amending `_canonical-model.md §3`. A new **work-item or project table** is never admissible: the card **is** an ERPNext Task; the project **is** an ERPNext Project.

Reviewers cite the row of this matrix that governs the change. If no row exists, the capability is out of scope until the matrix is extended.

---

## 2. THE MASTER MATRIX

Legend — **Decision:** REUSE / EXTEND / BUILD. **Mechanism:** as-is · custom field · workflow · fixture · report/chart · doc-event · permission hook · SPA view. **Effort:** S (hours) / M (days) / L (weeks). **Phase:** 1 (Reuse-First MVP) / 2 (Modern Experience) / 3 (Portfolio & Ecosystem), per canonical §10.

| # | Capability | Jira / Plane analog | ERPNext / Frappe component(s) | Decision | Mechanism | Effort | Phase | Notes / justification |
|---|---|---|---|---|---|---|---|---|
| 1 | Project container | Project / Project | **Project** | REUSE | as-is (+ custom fields, row 55) | S | 1 | Costing, billing, customer, cost center stay authoritative. Never cloned. |
| 2 | Work item / card | Issue / Issue | **Task** (`status`, `priority`, `type`, `exp_start_date`, `exp_end_date`, `%complete`) | REUSE | as-is (+ custom fields, row 54) | S | 1 | The Pulse card **is** a Task. One work-item table, ever. |
| 3 | Sub-tasks | Sub-task / Sub-issue | **Task.`parent_task`**, `is_group` | REUSE | as-is | S | 1 | Hierarchy already native. No new child-item table. |
| 4 | Hierarchy (Epic→Story→Sub-task) | Epic→Story→Sub-task | **Task.`parent_task`** + **Task Type** | REUSE/EXTEND | as-is + Task Type fixtures (row 8) | S | 1 | Levels expressed by `type` + `parent_task`, not new tables. |
| 5 | Dependencies | Issue links / Blocks | **Task.`depends_on`** (Task Depends On child) | REUSE | as-is | S | 1 | No Pulse dependency doctype. Retire `Pulse Task Dependency`. |
| 6 | Task/issue types | Issue Type | **Task Type** (`Task.type`) | EXTEND | fixture | S | 1 | Ship `Epic, Story, Bug, Task, Sub-task, Improvement, Incident, Feature`. No custom type field. |
| 7 | Story points / estimation | Story Points | **Task** + `pulse_story_points` | EXTEND | custom field (Float) | S | 1 | Estimation is an attribute of the work item. |
| 8 | Backlog ordering | Backlog rank | **Task** + `pulse_rank` | EXTEND | custom field (Int) | S | 1 | Ordering is an attribute; lower = higher. Retire any parallel ordering table. |
| 9 | Sprint / iteration | Sprint / Cycle | **Pulse Sprint** (new) + `Task.pulse_sprint` | BUILD + EXTEND | new doctype + custom field (Link) | M | 1 | **No ERPNext equivalent** — the one genuinely new *master*. Task↔Sprint via link, not data copy. |
| 10 | Board columns | Board columns | **Workflow States** on Task | EXTEND | workflow | M | 1 | Columns render from `Backlog→To Do→In Progress→In Review→Done (+Cancelled)`. Not a custom status field. |
| 11 | Kanban board (MVP) | Board / Board | **Kanban Board** (Frappe core) | REUSE | as-is | S | 1 | Ship a working board Phase 1 before any SPA. |
| 12 | Modern board (WIP, swimlanes, quick-add, inline edit) | Board polish | **Task** data via SPA | BUILD | SPA view | L | 2 | Front-end only, over the same Task rows. WIP/swimlanes are view config, not schema. |
| 13 | Workflow / transitions | Workflow / State machine | **Workflow / Workflow State / Workflow Action** | REUSE/EXTEND | as-is + `Pulse Task Workflow` fixture | M | 1 | Transitions role-gated (row 47). `Done`→Task `status=Completed` so costing/closure fire. |
| 14 | Epics | Epic | **Task Type = Epic** + `Task.pulse_epic` | EXTEND | fixture + custom field (Link→Task) | S | 1–2 | Epic is a Task, not a new hierarchy. Epic view is SPA (Phase 2). |
| 15 | Milestones | Milestone / — | **Task** `is_milestone` / **Project Update** | REUSE | as-is | S | 1 | Retire `Pulse Milestone`. Milestone = a Task flag or a status snapshot. |
| 16 | Releases / versions | Fix Version / — | **Task/Project** + `pulse_release` (Data; Link if Release doctype added) | EXTEND | custom field | S | 2 | Grouping attribute, not a work item. Light doctype only if v2 needs release reports. |
| 17 | Assignment (assignees) | Assignee | **ToDo / `_assign`** (Assignment) | REUSE | as-is | S | 1 | Card assignees via framework assignment. Retire member tables. |
| 18 | Role hierarchy (who may assign to whom) | Permission scheme | **Pulse Role Rank** + `Pulse Settings.role_ranks` | BUILD + EXTEND | new child doctype + permission hook + `validate` | M | 1 | Assign down/sideways only; enforced server-side via rank map. No ERPNext rank concept. |
| 19 | Roles | Roles | **Role / Role Profile / Has Role** | REUSE/EXTEND | as-is + role fixtures | S | 1 | Ship `Pulse Admin/Manager/Team Lead/Senior Dev/Junior Dev/Intern/Viewer`. |
| 20 | Timesheets / actuals | Worklog / — | **Timesheet + Timesheet Detail** | REUSE | as-is | S | 1 | "Actual effort" = timesheet hours. Never hand-entered. ERPNext differentiator. |
| 21 | Activity cost / rates | — / — | **Activity Type / Activity Cost** | REUSE | as-is | S | 1 | Billing & costing rates. No Plane/Jira equivalent. |
| 22 | Templates | Project templates | **Project Template / Project Template Task** | REUSE | as-is | S | 1 | Sprint/epic templates too. Retire any Pulse template concept. |
| 23 | Project updates / status | Project health | **Project Update** | REUSE | as-is | S | 1 | Periodic health capture already native. |
| 24 | Comments | Comments | **Comment / Communication** | REUSE | as-is | S | 1 | Framework timeline. No Pulse comment table. |
| 25 | Mentions | @mentions | **Comment mentions / Notification** | REUSE | as-is | S | 1 | `@user` mentions + notifications come free with the timeline. |
| 26 | Attachments | Attachments | **File / Attachments** | REUSE | as-is | S | 1 | Card attachments via File doctype. |
| 27 | Activity timeline / audit | Activity / History | **Activity Timeline / Version** | REUSE | as-is | S | 1 | Audit trail free. Metrics history handled by Status Log (row 50), not Version parsing. |
| 28 | Tags / labels | Labels | **Tag / `_user_tags`** | REUSE | as-is | S | 1 | Retire `Pulse Label` entirely. |
| 29 | Notifications | Notifications | **Notification / Notification Settings / Email** | REUSE | as-is + notification fixtures | S | 1 | Sprint/assignment alerts via framework. No custom notifier. |
| 30 | Calendar | Calendar | **Frappe Calendar view** (Task due dates) | REUSE | as-is | S | 1 | Due-date calendar free. |
| 31 | Gantt | — / — | **Frappe Gantt view** (Task) | REUSE | as-is | S | 1 | Timeline Phase 1. SPA roadmap enhances later (row 41). |
| 32 | Velocity report | Velocity chart | **Script/Query Report + Dashboard Chart** over Pulse Sprint | BUILD | report/chart | M | 1 | No native agile metric. Built on reporting engine, not a bespoke chart lib. |
| 33 | Burndown | Burndown | **Script Report + Chart** over Status Log + sprint dates + Holiday List | BUILD | report/chart | M | 1 | Needs timestamped transitions → Status Log (row 50). |
| 34 | Burnup | Burnup | **Script Report + Chart** over Status Log | BUILD | report/chart | M | 2 | Scope vs completed over time. |
| 35 | Cumulative Flow (CFD) | CFD | **Script Report + Chart** (count per state per day, Status Log) | BUILD | report/chart | M | 2 | Requires per-state daily counts. |
| 36 | Cycle time / lead time | Cycle/lead time | **Script Report** over Status Log timestamps | BUILD | report | M | 2 | Timestamp math over append-only log. |
| 37 | Workload | Workload / — | **Script Report** over `_assign` + `pulse_story_points` | BUILD | report/chart | S | 2 | Open points per assignee. |
| 38 | Sprint report | Sprint report | **Script Report** over Pulse Sprint + Status Log | BUILD | report | M | 2 | Planned vs completed, added/removed, spillover. |
| 39 | Dashboards | Dashboards | **Dashboard / Dashboard Chart** | REUSE | as-is | S | 1–2 | Compose the built charts; don't reinvent dashboards. |
| 40 | Number cards | Stat widgets | **Number Card** | REUSE/EXTEND | fixture | S | 1 | Ship agile number cards as fixtures. |
| 41 | Roadmap / timeline | Roadmap / Timeline | **Task** data via SPA (+ Gantt Phase 1) | BUILD | SPA view | L | 3 | Portfolio planning view; Gantt covers Phase 1. |
| 42 | Modules / cycles views | — / Modules & Cycles | **Pulse Sprint** (cycles) + `Task.pulse_epic`/Task Type (modules) via SPA | BUILD | SPA view | L | 3 | Presentation over existing entities; no new tables. |
| 43 | Pages / docs | Confluence / Pages | **Wiki / Web Page / File** (or light reuse) | REUSE | as-is | M | 3 | Reuse existing content doctypes; no Pulse pages table. |
| 44 | REST API | REST API | **Frappe REST / `@frappe.whitelist`** | REUSE/EXTEND | as-is + thin `pulse.api.*` endpoints | M | 1–2 | Standard document API for writes so permissions apply. No custom auth/session. |
| 45 | Search / filters | JQL / Filters | **Report Builder / list filters / `frappe.client`** | REUSE | as-is | S | 1 | Standard filtering; SPA adds lean board/backlog queries later. |
| 46 | Saved views | Saved filters | **List View settings / (SPA saved views)** | REUSE/BUILD | as-is → SPA view | M | 2 | Desk list settings Phase 1; SPA saved views Phase 2. |
| 47 | Workflow role-gating | Workflow permissions | **Workflow Action** allowed roles | EXTEND | workflow | S | 1 | Transition permissions declared in the workflow fixture. |
| 48 | User permissions / scoping | Project roles | **User Permission** (Project/Company) | REUSE | as-is | S | 1 | Project/company scoping via existing restriction engine. |
| 49 | Field security (financial fields) | Field config | **permlevel** on Task/Project fields | EXTEND | property setter / fixture | S | 1 | Delivery users cannot edit costing (permlevel > 0). |
| 50 | Status history for metrics | (implicit) | **Pulse Task Status Log** (new, append-only) | BUILD | new doctype + doc-event | M | 1 | Task has no per-status history; Version parsing too fragile. Feeds rows 33–38. |
| 51 | Automations | Automation rules | **Notification / Assignment Rule / Auto Repeat** | REUSE | as-is (surfaced in SPA later) | S–M | 3 | Reuse Frappe automation; expose in Pulse UI in Phase 3. |
| 52 | Holiday list / capacity | Working days / Capacity | **Holiday List** (`Pulse Settings.working_days_source`) | REUSE/EXTEND | as-is + settings link | S | 1–2 | Burndown working days & capacity from Holiday List. |
| 53 | App configuration | Project/instance settings | **Pulse Settings** (Single, new) | BUILD | new single doctype | S | 1 | Default sprint length, board type, hierarchy toggle, role ranks, working-days source. |
| 54 | Task custom fields (bundle) | Custom fields | **Task** + `pulse_*` fields | EXTEND | custom fields (fixture) | S | 1 | `pulse_section, pulse_story_points, pulse_sprint, pulse_epic, pulse_rank, pulse_release`. |
| 55 | Project custom fields (bundle) | Project config | **Project** + `pulse_*` fields | EXTEND | custom fields (fixture) | S | 1 | `pulse_section, pulse_enable_scrum, pulse_board_type, pulse_default_sprint_length, pulse_project_key`. |
| 56 | People / org | Members / Members | **User / Employee / Department** | REUSE | as-is | S | 1 | Retire `Pulse Team` / `Pulse Team Member`. Teams = ERPNext structures. |
| 57 | Financial dimensions | — / — | **Company / Cost Center / Customer** | REUSE | as-is | S | 1 | Money buckets inherited; the ERP moat. |
| 58 | Status-log write | (implicit) | **Task `on_update`** → Status Log | BUILD | doc-event | S | 1 | Append a log row when `workflow_state`/`status` changes; snapshot points. |
| 59 | Backlog view | Backlog | **Task** (`pulse_rank`, `pulse_sprint`) via list → SPA | REUSE/BUILD | as-is → SPA view | M | 1–2 | Desk list Phase 1; move-to-sprint & drag ordering in SPA. |

---

## 3. What we REUSE as-is (narrative)

The bulk of Pulse is **ERPNext, unmodified**. These components are consumed directly — no fields, no wrappers, no shadow copies:

- **The whole system of record.** `Project` is the container; `Task` is the card. Every hour lives in `Timesheet`/`Timesheet Detail`; every rate in `Activity Type`/`Activity Cost`; every financial dimension in `Company`/`Cost Center`/`Customer`. Because the card *is* a Task, costing, billing, gross-margin, and invoicing roll up automatically — the single feature Jira and Plane cannot match, and we get it for free by *not* cloning.
- **Work structure.** Sub-tasks and hierarchy via `Task.parent_task`/`is_group`; dependencies via `Task.depends_on`. No Pulse dependency or checklist-item table.
- **The framework plumbing.** Assignment (`ToDo`/`_assign`), comments and mentions (`Comment`/`Communication`), attachments (`File`), audit timeline (`Version`/Activity), notifications (`Notification`/Email), and access control (`Role`/`Role Profile`/`Has Role`/`DocPerm`/`User Permission`/`permlevel`) all apply the instant work is a core Task. Pulse writes **zero** code for any of these — the current build's re-implementations of assignment, notifications, and permissions are exactly what gets deleted.
- **Views that already ship.** Frappe **Kanban Board**, **Calendar**, and **Gantt** give a working board, due-date calendar, and timeline in Phase 1 with no custom UI. The **Report Builder / Query Report / Script Report / Dashboard Chart / Number Card / Dashboard** engine is the substrate for every metric — we build reports *on* it, never a parallel charting stack.
- **Repeatability & health.** `Project Template`/`Project Template Task` for repeatable structures; `Project Update` for status snapshots and milestone semantics.
- **The API and auth.** Frappe **REST** + `@frappe.whitelist` with standard session/CSRF. No custom authentication, ever.

---

## 4. What we EXTEND (custom fields, workflow, fixtures)

Extension changes **data and configuration, not the model**. All of it ships as **fixtures** so it is upgrade-safe and reproducible; none of it edits an ERPNext core file.

### 4.1 Custom fields (canonical §4)

**On `Task`** (fixture — Custom Field):

| fieldname | label | type | options / notes |
|---|---|---|---|
| `pulse_section` | Pulse | Section Break | tab/section for agile fields |
| `pulse_story_points` | Story Points | Float | estimation (row 7) |
| `pulse_sprint` | Sprint | Link → Pulse Sprint | Task↔Sprint link (row 9) |
| `pulse_epic` | Epic | Link → Task (filtered Task Type = Epic) | row 14 |
| `pulse_rank` | Backlog Rank | Int | ordering; lower = higher (row 8) |
| `pulse_release` | Release/Version | Data (Link if Release doctype added v2) | grouping (row 16) |

**On `Project`** (fixture — Custom Field):

| fieldname | label | type | options / notes |
|---|---|---|---|
| `pulse_section` | Pulse | Section Break | |
| `pulse_enable_scrum` | Enable Scrum | Check | opt-in agile per project |
| `pulse_board_type` | Board Type | Select `Scrum,Kanban` | |
| `pulse_default_sprint_length` | Default Sprint Length (days) | Int | default from Pulse Settings |
| `pulse_project_key` | Project Key | Data | short key e.g. "PLS" (optional) |

Board columns and agile statuses come from **Workflow** (below), **not** a custom status field; issue types come from **Task Type**, **not** a custom type field.

### 4.2 Workflow (canonical §5)

- **Pulse Task Workflow** on `Task`: states `Backlog → To Do → In Progress → In Review → Done (+ Cancelled)` shipped as a **Workflow fixture**. `workflow_state` is Frappe-managed; board columns render from these states. Transitions are **role-gated** via Workflow Action allowed-roles. Reaching `Done` maps Task `status = Completed` (via workflow field mapping / doc-event) so core costing and closure still fire.

### 4.3 Fixtures & hooks

- **Task Type** records (row 6); **Roles** (row 19); **Number Cards** and **Notifications** (rows 40, 29) as fixtures.
- **`permlevel`** on financial Task/Project fields (row 49) via property setter/fixture.
- **Doc-event** `Task.on_update` → write a `Pulse Task Status Log` row on state change (row 58).
- **Permission hook** — `permission_query_conditions` + a `validate` assignment check enforcing the role-rank hierarchy (row 18), driven by `Pulse Settings.role_ranks`. Base DocPerm still governs CRUD; the rank rule is an *additional* constraint, enforced server-side, never UI-only.

---

## 5. What we BUILD (and why nothing else)

Only four new doctypes exist, plus the SPA and the metric reports. Each passes the gate: **no ERPNext equivalent.**

### 5.1 The four new doctypes (canonical §3)

1. **Pulse Sprint** *(master)* — **no ERPNext equivalent.** ERPNext has projects, tasks, templates, and updates, but **no iteration/time-box** concept. Holds `sprint_name, project (Link→Project), status (Planned/Active/Completed), start_date, end_date, goal, planned_points, completed_points, velocity, is_active`. One **Active** sprint per project (validate). Tasks join via `Task.pulse_sprint` — a link, never a data copy.
2. **Pulse Task Status Log** *(append-only log)* — **no ERPNext equivalent.** Task has **no per-status history**, and parsing the Version log for transitions is fragile. This write-once log (`task, project, sprint, from_state, to_state, changed_by, changed_on, points_at_change`) is the *only* reliable source for burndown, burnup, CFD, and cycle/lead time. Written by the `Task.on_update` doc-event; never edited/deleted by users (read-only perms / permlevel).
3. **Pulse Settings** *(Single)* — **no equivalent** app-config surface. Holds `default_sprint_length_days, default_board_type, enable_hierarchical_assignment, email/desktop notification toggles, role_ranks (table), working_days_source (Link→Holiday List)`. Reuses/renames the existing Pulse Settings single; obsolete fields dropped.
4. **Pulse Role Rank** *(child of Pulse Settings)* — **no equivalent.** ERPNext roles have no rank/seniority ordering. `role (Link→Role), rank (Int, higher=senior)`. Drives the hierarchical-assignment rule.

No other new doctype is admissible without first amending `_canonical-model.md §3`.

### 5.2 The SPA (front-end)

Frappe UI (Vue 3 + frappe-ui) SPA at `/pulse` (Gameplan/Helpdesk pattern) — modern Board, Backlog, Sprint, Rich Task pane; later Roadmap/Timeline, Modules & Cycles. **Justification:** ERPNext's back-end is complete but its Desk UX cannot reach Plane-grade interaction (drag, quick-add, inline edit, command-k). The SPA is a *view over core Task/Project data* through thin whitelisted APIs — it adds **no** back-end tables and duplicates **no** server logic. This is where the custom-code budget is deliberately spent.

### 5.3 The metric reports

Velocity, Burndown, Burnup, CFD, Cycle/Lead time, Workload, Sprint report — all as **Script/Query Reports + Dashboard Charts + Number Cards** over Task + Status Log + Pulse Sprint + Timesheet. **Justification:** ERPNext reporting is finance-oriented and ships **no** agile metrics; but the *report/chart engine itself is reused* — Pulse writes the queries, not a charting framework. Actual-hours metrics always derive from Timesheet, never a hand-entered field.

**Why nothing else:** every remaining capability in §2 resolves to REUSE or EXTEND. There is no admissible fifth doctype, no parallel work-item table, no custom auth, no custom notifier, no custom charting stack.

---

## 6. Retirement plan (deprecated Pulse* → core replacement)

The parallel data model is retired. Each old doctype maps to a core replacement; a one-time migration moves data into core Task/Project, then the old doctype is dropped.

| Deprecated doctype | Core replacement | Mechanism / migration |
|---|---|---|
| `Pulse Project` | **Project** | Migrate rows → Project; agile flags → `pulse_*` custom fields on Project (row 55). |
| `Pulse Task` | **Task** | Migrate rows → Task; story points/sprint/rank/type → `pulse_*` fields + Task Type (rows 54, 6). |
| `Pulse Team` | **User / Department / Role Profile / Project User** | Teams are ERPNext org structures; no team table. |
| `Pulse Team Member` | **Has Role / Project User / `_assign`** | Membership via roles/assignment. |
| `Pulse Project Member` | **Project User** (child) + assignment | Project access via Project Users + User Permission. |
| `Pulse Milestone` | **Task** (`is_milestone`) / **Project Update** | Milestone = a Task flag or a status snapshot (row 15). |
| `Pulse Label` | **Tag / `_user_tags`** | Labels → tags (row 28). |
| `Pulse Task Dependency` | **Task.`depends_on`** (Task Depends On) | Dependencies native (row 5). |
| `Pulse Checklist Item` | **Task sub-tasks** (`parent_task`) *(or light checklist child only if truly needed)* | Prefer sub-tasks; extend only if unavoidable. |
| Old `Pulse Settings` (obsolete fields) | **Pulse Settings** (rebuilt) | Keep/rename the Single; drop obsolete fields, add canonical §3.3 fields. |

Also retired by construction: the custom API layer's `ignore_permissions=True` writes, the hand-built assignment/notification/permission services, the destructive nightly overdue job, and the broken sync doc-events — all replaced by the standard document API, framework services, and the workflow/doc-event/permission-hook extensions above.

---

## 7. Reuse scorecard

Counting the 59 capability rows in §2 by decision (rows spanning two buckets counted toward their primary decision):

| Bucket | Approx. share | What it covers |
|---|---|---|
| **REUSE (as-is)** | **~65%** | Project, Task, hierarchy, dependencies, timesheets, rates, templates, updates, assignment, comments, mentions, attachments, timeline, tags, notifications, calendar, gantt, Kanban board, roles, user permissions, REST, search, dashboards, people/org, financial dimensions, holiday list, automations. |
| **EXTEND (custom field / workflow / fixture / hook)** | **~20%** | Story points, sprint link, epic link, backlog rank, release field, Task Types, workflow + role-gating, permlevel field security, project agile flags, role fixtures, number cards. |
| **BUILD (new doctype / SPA / report)** | **~15%** | 4 new doctypes (Pulse Sprint, Pulse Task Status Log, Pulse Settings, Pulse Role Rank), the SPA views, and the 7 metric reports/charts — all still *over* core Task/Project. |

This satisfies objective **O4 (≥ 70% delivered via reuse/extension)** — roughly **85% reuse + extend, ~15% net-new** — and the ~15% BUILD is concentrated in the front-end and metrics (canonical §9, analysis §17–§18), exactly where ERPNext genuinely lacks an equivalent. No new work-item or project table exists anywhere in Pulse.

---

*End of Document 5 — ERPNext Reuse Matrix. This is the contract; every PR is measured against it. Next: Document 6.*
