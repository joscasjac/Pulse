# Pulse — Project Overview

**Document 1 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. Purpose & Scope

**Pulse** is a reuse-first, agile project-management application for ERPNext. It adds the agile operating model (sprints, backlog, story points, epics, velocity, burndown) and a modern delivery-team experience (fast Kanban board, backlog, roadmap, rich task view) **on top of ERPNext Projects — without forking the data model.**

The defining architectural decision: **a Pulse card *is* an ERPNext Task; a Pulse project *is* an ERPNext Project.** Pulse never keeps a shadow copy of work items. All costing, billing, timesheets, assignment, comments, attachments, notifications and permissions come free from the ERPNext/Frappe framework.

**Scope of this document:** establish *what Pulse is*, the problem it solves, the solution shape, in/out-of-scope boundaries by phase, target users, shared vocabulary, assumptions, dependencies, the three-layer architecture, success criteria, and the map of all 21 documents. It is the on-ramp to the rest of the documentation set and inherits every decision made in Document 0 (Enterprise Analysis) and `_canonical-model.md` (single source of truth).

---

## 2. Problem Statement

ERPNext ships a capable, financially-integrated project engine — **Project, Task** (hierarchy, dependencies, templates), **Timesheet, Activity Type/Cost, Project Update**, plus framework-wide assignment, comments, notifications, workflow, permissions, dashboards and reports. What it lacks:

1. **No agile model.** Sprint, Backlog, Story Points, Epic, Velocity, Burndown/Burnup, cycle/lead time are not first-class concepts.
2. **Dated UX.** The Task list/Gantt/Kanban are functional but slow and dense compared to Jira/Plane.
3. **Weak board experience.** Frappe Kanban lacks WIP limits, swimlanes, sprint scoping, quick-add and inline-edit polish.
4. **No roadmap / timeline / modules-and-cycles** portfolio planning views.
5. **Manual assignment hierarchy.** No built-in enforcement of "who may assign to whom".
6. **Finance-oriented reporting**, not delivery-oriented (no velocity, sprint report or burndown out of the box).
7. **Limited rich task view** — no single-pane task detail with sub-tasks, checklist, activity, dependencies and story points together.

Teams therefore buy a **separate Jira or Plane subscription** and run delivery *outside* ERPNext, degrading the data quality upstream of finance and creating tool sprawl. A parallel earlier build of this app compounded the problem by cloning ERPNext into `Pulse Project`/`Pulse Task`/etc. — data never reached ERPNext costing/billing/timesheets, and every feature had to be hand-built. That approach is deprecated.

---

## 3. Solution Summary

Pulse is a **thin agile-and-experience layer over ERPNext Projects**, not a second project system:

- **ERPNext = system of record.** Costing, billing, timesheets, accounting, customer and margin stay authoritative and unchanged.
- **Pulse = system of engagement.** Sprints, boards, roadmap, modern UI and hierarchical assignment, storing agile-specific data as *extensions of core doctypes*, not replacements.

Concretely, Pulse:

- **Reuses** Project, Task, Timesheet, Activity Cost, Project Update, Workflow, Assignment (`_assign`/ToDo), Comments, Attachments, Notifications, Roles/Permissions, Reporting engine, Calendar/Gantt, and REST API **as-is**.
- **Extends** Task and Project with `pulse_*` custom fields (story points, sprint link, backlog rank, epic, release, agile flags), reuses **Task Type** for issue types, and expresses agile statuses via a **Frappe Workflow** — not a new status field.
- **Builds** only what has no ERPNext equivalent: four new doctypes — **Pulse Sprint, Pulse Task Status Log, Pulse Settings, Pulse Role Rank** — plus metric reports/charts and (Phase 2+) a Frappe-UI SPA.

**One-line positioning:** *"Jira-grade agile + Plane-grade UX, natively financially integrated — because every card is an ERPNext Task."*

---

## 4. In-Scope / Out-of-Scope (by Phase)

The authoritative phase roadmap lives in `_canonical-model.md §10`. Summary:

### Phase 1 — Reuse-First Foundation (MVP) — IN SCOPE
- App rename/cleanup; fix install & hooks (retire deprecated `Pulse *` doctypes).
- Custom fields on **Task** (`pulse_story_points`, `pulse_sprint`, `pulse_epic`, `pulse_rank`, `pulse_release`, `pulse_section`) and **Project** (`pulse_enable_scrum`, `pulse_board_type`, `pulse_default_sprint_length`, `pulse_project_key`).
- **Task Type** fixtures (Epic, Story, Bug, Task, Sub-task, Improvement, Incident, Feature).
- **Pulse Task Workflow** (Backlog → To Do → In Progress → In Review → Done, + Cancelled).
- **Pulse Sprint**, **Pulse Task Status Log**, **Pulse Settings** + **Pulse Role Rank**.
- Pulse roles + hierarchical assignment hook (assign-down/sideways only).
- Status-log doc-event; reuse Frappe **Kanban Board**; **Velocity** + **Burndown** (report + chart); Desk **Pulse workspace**.
- One-time migration of any old Pulse* data into core Task/Project.
- Financial integration inherited automatically (cards are Tasks).

### Phase 2 — Modern Experience — OUT OF MVP, IN ROADMAP
- Frappe-UI (Vue 3) SPA at `/pulse`: Board, Backlog, Sprint, Rich Task pane.
- Burnup, Cumulative Flow Diagram, Cycle/Lead time.
- WIP limits, swimlanes, saved filters, Epics view.

### Phase 3 — Portfolio & Ecosystem — OUT OF MVP, IN ROADMAP
- Roadmap/Timeline, Modules & Cycles views, Releases + release report.
- Pages/Docs per project, automations UI, plugin/extension API, mobile/PWA.

### Explicitly OUT (all phases, non-goals)
- A parallel work-item table or any new `Pulse Project`/`Pulse Task` doctype.
- Custom auth/session/CSRF (reuse Frappe).
- Re-implementing assignment, notifications or permissions in app code.
- Full 1:1 Jira feature parity; hand-entered "actual hours" (actuals come from Timesheet).

---

## 5. Target Users

| User | Role fixture | Primary use of Pulse |
|---|---|---|
| Platform / app admin | `Pulse Admin` | Install, configure Pulse Settings, role ranks, workflow, fixtures |
| Project / delivery manager | `Pulse Manager` | Plan sprints, triage backlog, review burndown/velocity, assign down |
| Team lead | `Pulse Team Lead` | Run daily board, assign to developers, manage sprint scope |
| Senior developer | `Pulse Senior Developer` | Own stories, assign sub-tasks down, estimate, move cards |
| Junior developer | `Pulse Junior Developer` | Work assigned cards, log time via Timesheet, update status |
| Intern | `Pulse Intern` | Work assigned cards; cannot assign to others above rank |
| Viewer / stakeholder | `Pulse Viewer` | Read-only boards, roadmaps, reports |
| Finance / client stakeholder | (ERPNext roles) | Consume costing/billing in Desk; delivery data flows from Pulse |

Detailed personas with goals and pains are in Document 2 (PRD).

---

## 6. Glossary of Terms

### Agile terms
| Term | Meaning in Pulse |
|---|---|
| **Sprint** | Time-boxed iteration. Implemented as the **Pulse Sprint** doctype linked to a Project. |
| **Backlog** | Ordered pool of un-sprinted / not-started Tasks, ranked by `pulse_rank`. Not a doctype — a view over Tasks. |
| **Epic** | Large body of work grouping stories. A **Task** with **Task Type = Epic**; child tasks link via `pulse_epic` and/or `parent_task`. |
| **Story / Issue / Card** | The unit of work. **IS an ERPNext Task.** |
| **Sub-task** | A Task with `parent_task` set (Task Type = Sub-task). |
| **Story Point** | Relative estimate of effort/complexity. `pulse_story_points` (Float) on Task. |
| **Velocity** | Completed story points per closed sprint. Computed on Pulse Sprint / reported. |
| **Burndown** | Remaining story points vs. day across a sprint. Derived from Pulse Task Status Log + sprint dates + working days. |
| **Burnup** | Completed points vs. total scope over time (Phase 2). |
| **Cumulative Flow Diagram (CFD)** | Count of cards per workflow state per day (Phase 2), from Status Log. |
| **Cycle Time** | Elapsed time from work-start (In Progress) to Done, from Status Log timestamps. |
| **Lead Time** | Elapsed time from creation/Backlog to Done. |
| **WIP limit** | Max cards allowed in a board column (Phase 2). |
| **Swimlane** | Horizontal board grouping, e.g. by assignee or epic (Phase 2). |
| **Release / Version** | Grouping of work for shipment. `pulse_release` field (Phase 1); optional Release doctype (v2). |
| **Board column** | A **Frappe Workflow state** (Backlog/To Do/In Progress/In Review/Done). Not a custom status field. |

### ERPNext / Frappe terms
| Term | Meaning |
|---|---|
| **Project** | ERPNext container with costing/billing/customer. A Pulse project IS a Project. |
| **Task** | ERPNext work item (`parent_task`, `is_group`, `depends_on`, `type`, `priority`, `status`, `exp_start/end_date`, `%complete`). The Pulse card. |
| **Task Type** | Master driving issue-type semantics (Epic, Story, Bug, …). |
| **Timesheet / Timesheet Detail** | Real time capture; source of "actual hours". |
| **Activity Type / Activity Cost** | Billing & costing rates. |
| **Project Template / Project Template Task** | Repeatable project/task structures. |
| **Project Update** | Periodic project health/status snapshot. |
| **ToDo / `_assign`** | Framework assignment mechanism = card assignees. |
| **Workflow / Workflow State / Workflow Action** | Transition engine = board columns and gated transitions. |
| **Version** | Frappe change-audit log. |
| **Role / Role Profile / Has Role / DocPerm / User Permission / permlevel** | RBAC building blocks. |
| **Holiday List** | Working-days source for burndown. |
| **Dashboard Chart / Number Card / Query Report / Script Report** | Reporting engine Pulse builds metrics on. |
| **Fixtures** | Reproducible shipping of custom fields, roles, workflows, etc. |
| **Single doctype** | A doctype with exactly one record (e.g. Pulse Settings). |

---

## 7. Assumptions

1. A working Frappe **v16.25** bench with **ERPNext v16.26** installed; ERPNext Projects module enabled.
2. Users are managed via Frappe **User** (optionally linked to **Employee**); org structure via **Department/Company/Cost Center**.
3. Delivery teams will log time through **Timesheet**; actual effort is never hand-entered on cards.
4. Agile is **opt-in per project** via `pulse_enable_scrum`; non-agile projects keep classic ERPNext behavior.
5. Only **one Active sprint per project** at a time (validated in Pulse Sprint).
6. Installations are **upgrade-safe**: all additions via fixtures/custom fields/new module; **no core file edits, no monkey-patching**.
7. The reader has approved Document 0's re-baseline recommendation; deprecated `Pulse *` doctypes are being retired, not extended.

---

## 8. Dependencies (ERPNext / Frappe modules)

| Dependency | Why Pulse needs it |
|---|---|
| **Frappe framework** (v16.25) | Doctypes, workflow, permissions, assignment, notifications, REST API, reporting, fixtures |
| **ERPNext Projects** | Project, Task, Task Type, Project Template, Project Update |
| **ERPNext Time / Timesheet** | Timesheet, Timesheet Detail (actual effort) |
| **ERPNext Setup / Activity** | Activity Type, Activity Cost (rates) |
| **ERPNext HR/Org masters** | Employee, Department, Holiday List, Company, Cost Center, Customer |
| **Frappe Kanban Board** | Phase-1 board experience |
| **Frappe Desk / Workspace** | Phase-1 navigation and views |
| **frappe-ui (Vue 3)** | Phase-2 SPA (pattern: Gameplan/Helpdesk) |

Pulse ships as a standard Frappe app (`bench get-app` → `bench install-app pulse`) with fixtures. No third-party SaaS dependency.

---

## 9. High-Level Three-Layer Architecture (recap)

```
┌─────────────────────────────────────────────────────────────┐
│  EXPERIENCE (Pulse)                                          │
│  Modern UI: Board · Backlog · Sprint · Roadmap · Rich Task   │
│  Phase 1: Frappe Kanban + Desk workspace                     │
│  Phase 2+: Frappe UI (Vue 3) SPA at /pulse                   │
└───────────────▲─────────────────────────────────────────────┘
                │ Frappe REST / thin whitelisted endpoints (pulse.api.*)
┌───────────────┴─────────────────────────────────────────────┐
│  AGILE LAYER (Pulse — thin)                                  │
│  Pulse Sprint · Task Status Log · Settings · Role Rank ·     │
│  metric reports · doc-events (status log, rank) ·            │
│  permission hooks (hierarchical assignment)                  │
└───────────────▲─────────────────────────────────────────────┘
                │ extends via Custom Fields (pulse_*) + link fields
┌───────────────┴─────────────────────────────────────────────┐
│  SYSTEM OF RECORD (ERPNext core — unchanged)                 │
│  Project · Task · Timesheet · Activity Cost · Project Update │
│  Workflow · Assignment · Comments · Notifications · Reports  │
│  Company · Customer · Department · Cost Center · Holiday List │
└─────────────────────────────────────────────────────────────┘
```

**Back-end principle:** thin. Endpoints return lean board/backlog payloads; all writes go through the standard document API so validations, permissions and doc-events fire normally — **never** blanket `ignore_permissions=True`.

---

## 10. Success Criteria

| # | Criterion | Measure |
|---|---|---|
| S1 | Agile added to ERPNext Projects | A team plans & runs a sprint end-to-end on core Task data |
| S2 | Modern, fast board | Board loads < 1s for 500 tasks; common actions ≤ 2 clicks |
| S3 | 100% financial integration preserved | Every Pulse task rolls up to Project costing/billing unchanged |
| S4 | Minimal custom code | ≥ 70% of features via reuse/extension (per Reuse Matrix) |
| S5 | Hierarchical assignment enforced | Senior assigns down; junior cannot assign up — enforced server-side |
| S6 | Upgrade-safe | Zero core-file edits; all additions via fixtures/custom fields/new module |
| S7 | Open-source ready | Clean install, docs, tests, contribution guide |
| S8 | Reliable metrics | Velocity & burndown reproducible from Status Log |

---

## 11. Document Map (all 21 documents)

| # | Document | Purpose |
|---|---|---|
| 0 | Pulse Enterprise Analysis | Foundational analysis; why Pulse, reuse-first thesis, defect audit |
| **1** | **Project Overview** *(this document)* | What Pulse is, scope, glossary, dependencies, doc map |
| 2 | Product Requirements Document (PRD) | Vision, personas, journeys, features (MoSCoW/phase), user stories, NFRs, KPIs |
| 3 | Business Requirements | Objectives, as-is/to-be, business rules, ROI, stakeholders, risks |
| 4 | Functional Requirements | Detailed functional specs per feature/module |
| 5 | ERPNext Reuse Matrix | The contract: every capability → reuse/extend/build, preventing re-cloning |
| 6 | Data Model & DocType Design | Fields, links, indexes for new doctypes + custom fields |
| 7 | Custom Fields & Fixtures Spec | Exact `pulse_*` fields, Task Types, roles, workflow as fixtures |
| 8 | Workflow & Status Design | Pulse Task Workflow states, transitions, board mapping |
| 9 | Permissions & Security Design | RBAC, permlevel, hierarchical assignment enforcement |
| 10 | Sprint & Backlog Design | Sprint lifecycle, backlog ordering, capacity |
| 11 | Board & UI Specification | Board, backlog, rich task, workspace; Phase-1 vs SPA |
| 12 | Metrics & Reporting Design | Velocity, burndown, burnup, CFD, cycle/lead time formulas |
| 13 | API Specification | Whitelisted `pulse.api.*` endpoints and contracts |
| 14 | Front-End Architecture | frappe-ui SPA structure, routing, API client |
| 15 | Notifications & Automation | Notification/assignment-rule reuse for alerts |
| 16 | Migration Plan | One-time Pulse*→core Task/Project migration |
| 17 | Testing Strategy | Unit/integration tests for Pulse extensions |
| 18 | Deployment & Install Guide | bench install, fixtures, config, upgrade guidance |
| 19 | Non-Functional & Performance | Performance, scalability, security, upgrade-safety targets |
| 20 | Roadmap & Release Plan | Phase 1/2/3 milestones and release strategy |
| 21 | Open-Source & Contribution Guide | Licensing, CONTRIBUTING, reuse gate, community |

*(Document numbering is authoritative; titles may be refined in later docs but the count remains 21 plus Document 0.)*

---

*End of Document 1. Proceed to Document 2 — Product Requirements Document.*
