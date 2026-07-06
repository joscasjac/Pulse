# Pulse — Enterprise Software Analysis

**Document 0 of 21 · Foundational Analysis (pre-documentation, pre-coding)**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25.0 · ERPNext v16.26.1
**Status:** Analysis phase. No new code to be written until the documentation set is approved.
**Prepared by (roles):** Principal ERPNext Solution Architect · Senior Frappe Developer · Enterprise Architect · Product Manager · Jira/Plane Product Architects · UX Architect · Database Architect · Agile Coach · Engineering Lead.

---

## How to read this document

This is the **analysis that precedes the documentation set**. It does not design the database or the screens — it decides *what* Pulse is, *why* it should exist, *what of ERPNext it must reuse*, and *what (little) it may add*. Every later document (PRD, Functional Requirements, Reuse Matrix, DB Design, etc.) inherits the decisions made here.

One rule governs everything below:

> **Reuse ERPNext → Extend ERPNext → Build new (only if unavoidable).**

Where the current build violated that rule, this document says so plainly and proposes the corrected path.

---

## 1. Executive Summary

ERPNext already contains a capable, financially-integrated project engine: **Project**, **Task** (with dependencies, hierarchy, templates), **Timesheet**, **Activity Type/Cost**, **Project Update**, plus assignments, ToDos, comments, workflows, notifications, dashboards and reports shared framework-wide. What it lacks is the **agile operating model** (sprints, backlog, story points, epics, velocity/burndown) and the **modern product experience** (fast Kanban, workspace navigation, roadmap/timeline, rich task view) that teams now expect from Jira and Plane.

**Pulse** closes that gap **without forking the data model**. It is positioned as a *thin agile-and-experience layer on top of ERPNext Projects* — not a second project system. The strategic thesis:

- ERPNext = **system of record** (costing, billing, timesheets, accounting, customer, margin). This stays authoritative.
- Pulse = **system of engagement** (sprints, boards, roadmap, modern UI, hierarchical assignment). This adds agile semantics and a delightful front-end, storing agile-specific data as *extensions of core doctypes*, not replacements.

**Critical finding on the current build.** The existing `pulse` app took the opposite approach: it created ~10 parallel `Pulse *` DocTypes (`Pulse Project`, `Pulse Task`, `Pulse Team`, `Pulse Milestone`, …) that re-implement ERPNext Projects. This is the direct cause of it "not working as expected": data entered in Pulse never reaches ERPNext costing/billing/timesheets, none of Frappe's assignment/permission/report machinery applies automatically, and every feature must be hand-built and hand-maintained. **The recommended architecture retires the parallel doctypes and rebuilds Pulse as an extension layer.** Details in §11–§18.

**Recommendation:** Proceed, but re-baseline. Keep the app name, the vision, and any reusable front-end code; discard the parallel data model. Adopt the reuse matrix in §16–§18. Ship an MVP that is *ERPNext core + Sprint/Backlog + a modern board* before anything else.

---

## 2. Product Vision

> **Pulse makes ERPNext feel like Jira and Plane — while every hour, cost, and invoice still lives in ERPNext.**

A team plans a sprint, drags cards across a board, tracks a burndown, and reviews a roadmap in a fast modern UI. Behind the glass, each card *is* an ERPNext Task, each logged hour *is* an ERPNext Timesheet line, each project *is* an ERPNext Project with real costing and billing. There is one source of truth, two experiences on top of it: the classic ERPNext Desk for finance/ops, and Pulse for delivery teams.

---

## 3. Mission Statement

To deliver the **best open-source project-management experience for ERPNext** by extending — never duplicating — the framework, so organizations get modern agile delivery *and* end-to-end financial integration from a single install, with the least custom code that is responsibly possible.

---

## 4. Product Philosophy

1. **One source of truth.** A task exists once, as an ERPNext Task. Pulse never keeps a shadow copy.
2. **Reuse beats extend; extend beats build.** Every proposed feature must first be checked against existing ERPNext/Frappe capability.
3. **Configuration over customization.** Prefer settings, custom fields, workflows, and property setters over Python.
4. **The framework does the plumbing.** Permissions, assignment, comments, timeline, attachments, notifications, audit trail, REST API — all come free from Frappe. Pulse must not re-implement them.
5. **Experience is a first-class feature.** ERPNext's weakness is UX, so Pulse invests its custom-code budget primarily in the front-end, not the back-end.
6. **Upgrade-safe.** Extensions must survive ERPNext upgrades: fixtures, custom fields, and a dedicated module — no core file edits, no monkey-patching of core doctypes.
7. **Progressive disclosure.** Simple for a 3-person team; scalable to a portfolio. Agile features are opt-in per project.

---

## 5. Project Objectives

| # | Objective | Success measure |
|---|-----------|-----------------|
| O1 | Add agile (Scrum/Kanban) to ERPNext Projects | A team can plan & run a sprint end-to-end on core Task data |
| O2 | Deliver a modern PM UI (board, backlog, roadmap, rich task) | Task interactions ≤ 2 clicks; board loads < 1s for 500 tasks |
| O3 | Preserve 100% of ERPNext financial integration | Every Pulse task rolls up to Project costing/billing unchanged |
| O4 | Minimize custom code | ≥ 70% of features delivered via reuse/extension, measured in Reuse Matrix |
| O5 | Hierarchical, role-based work assignment | Senior can assign down the hierarchy; junior cannot assign up |
| O6 | Upgrade-safe & maintainable | Zero core-file edits; all additions via custom fields/fixtures/new module |
| O7 | Open-source ready | Clean install, docs, tests, contribution guide |

---

## 6. Business Goals

- **Reduce tool sprawl / cost:** replace a separate Jira/Plane subscription for ERPNext shops.
- **Increase billable accuracy:** agile execution feeding real timesheets → better project margin visibility.
- **Adoption:** give delivery teams a reason to work *inside* ERPNext instead of around it, improving data quality upstream of finance.
- **Community leadership:** become the reference agile-PM app in the Frappe ecosystem (like HRMS is for HR).
- **Services upside:** a strong OSS core creates implementation/customization opportunities.

---

## 7. Problems with ERPNext Projects

*(Product/functional gaps — the reasons this app should exist.)*

1. **No agile model.** No Sprint, Backlog, Story Points, Epic, Velocity, Burndown/Burnup, cycle/lead time as first-class concepts.
2. **Dated UX.** The Task list/Gantt/Kanban are functional but slow, dense, and not delivery-team-friendly compared to Jira/Plane.
3. **Weak board experience.** Kanban exists in Frappe but lacks WIP limits, swimlanes, sprint scoping, quick-add, inline edit polish.
4. **No roadmap / timeline / modules/cycles** in the Plane sense (portfolio-level planning views).
5. **Hierarchy of assignment is manual.** ToDo/assignment exist but there's no built-in role-hierarchy enforcement ("who may assign to whom").
6. **Reporting is finance-oriented,** not delivery-oriented (no velocity chart, no sprint report, no burndown out of the box).
7. **Rich task view is limited** — no modern single-pane task detail with sub-tasks, checklist, activity, dependencies, story points in one view.

### 7b. Problems with the *current Pulse build* (implementation, not ERPNext)

- **Parallel data model:** `Pulse Project`/`Pulse Task`/etc. duplicate ERPNext, so costing, billing, timesheets, and standard reports do **not** apply. *(Primary root cause of "not working as expected".)*
- **Re-implemented plumbing:** custom API/services/scheduler code re-does assignment, notifications, and permissions that Frappe already provides — more surface area, more bugs.
- *(A concrete, file-level defect list is being compiled and will be attached as Appendix A.)*

---

## 8. Strengths of ERPNext Projects (what we must NOT lose)

- **Financial integration:** Project costing, gross margin, billing, Sales Order / Purchase linkage, accounting.
- **Timesheets & Activity Cost:** real time capture with billing/costing rates → payroll & invoicing.
- **Task hierarchy & dependencies:** `parent_task`, `task_depends_on`, `Dependent Task`.
- **Project Templates:** repeatable project/task structures.
- **Project Update:** periodic status/health capture.
- **Framework services:** Assignment (ToDo), Comments, Activity Timeline, Attachments, Notifications, Workflow, Roles/Permissions, Dashboard Charts, Report Builder & Query/Script Reports, Calendar, REST API — all free and consistent.
- **Master data:** Company, Customer, Department, Cost Center, Holiday List, User/Employee.

---

## 9. Why Plane is Better (experience & modern PM)

- Clean, fast, opinionated **UI/UX**; keyboard-first, low-friction.
- **Workspaces** and clear navigation hierarchy.
- **Cycles** (time-boxes) and **Modules** (feature groupings) as intuitive planning primitives.
- **Roadmap / timeline** views; visual portfolio planning.
- **Rich issue view:** properties, sub-issues, links, attachments, activity in one pane.
- **Pages/Docs** attached to projects.
- Beautiful empty states, drag-and-drop, inline editing.

**Take for Pulse:** the *experience patterns* (board, roadmap, rich task pane, workspace nav, cycles/modules-as-views), implemented over ERPNext data.

## 10. Why Jira is Better (agile depth & process)

- Mature **Scrum & Kanban**: backlog, sprint planning/execution/review, WIP limits, swimlanes.
- **Epics → Stories → Sub-tasks → Story Points**; estimation and hierarchy.
- **Agile metrics:** velocity, burndown, burnup, cumulative flow, cycle & lead time, control charts.
- **Workflows & transitions** with conditions/validators/post-functions.
- **Releases/Versions** and release reports.
- **Powerful filtering/JQL** and saved views; dashboards.
- **Granular, schemeable permissions** per project.

**Take for Pulse:** the *agile process model and metrics*, mapped onto ERPNext Task + a thin Sprint layer, using Frappe Workflow for transitions.

---

## 11. Gap Analysis (summary)

| Capability | ERPNext today | Jira | Plane | Pulse action |
|---|---|---|---|---|
| Project/Task/hierarchy/deps | ✅ | ✅ | ✅ | **Reuse** |
| Timesheets, costing, billing | ✅ (strong) | ⚠️ (add-ons) | ❌ | **Reuse (differentiator)** |
| Templates, updates | ✅ | ⚠️ | ⚠️ | **Reuse** |
| Assignment / ToDo / comments / timeline | ✅ | ✅ | ✅ | **Reuse** |
| Workflow engine | ✅ | ✅ | ⚠️ | **Reuse (configure)** |
| Sprint / iteration | ❌ | ✅ | ✅ (cycle) | **Extend: add Sprint doctype + link** |
| Backlog | ❌ | ✅ | ✅ | **Extend: view + fields** |
| Story points / estimation | ❌ | ✅ | ✅ | **Extend: custom field on Task** |
| Epic | ⚠️ (via parent/type) | ✅ | ✅ (module) | **Extend: Task Type/field, not new hierarchy** |
| Velocity / burndown / burnup | ❌ | ✅ | ✅ | **Build: reports/charts (reuse chart engine)** |
| Cycle/lead time | ❌ | ✅ | ⚠️ | **Build: script report over status history** |
| Modern board (WIP, swimlanes) | ⚠️ (basic) | ✅ | ✅ | **Build: front-end over Task** |
| Roadmap / timeline | ⚠️ (Gantt) | ✅ | ✅ | **Build/enhance front-end** |
| Rich task pane | ⚠️ | ✅ | ✅ | **Build: front-end over Task** |
| Role-hierarchy assignment rules | ❌ | ⚠️ | ⚠️ | **Extend: permission query + validation** |

Legend: Reuse = use as-is · Extend = custom fields/child tables/settings on core · Build = new UI or report (still over core data).

---

## 12. SWOT Analysis

**Strengths**
- Built on a mature ERP with real financial integration (a moat Jira/Plane lack).
- Frappe gives permissions, API, workflow, notifications for free.
- Single install, single data model, single login.

**Weaknesses**
- ERPNext desk UX is dated → must invest heavily in front-end.
- Small maintainer bandwidth; every custom line is a liability.
- Current build already carries technical debt (parallel doctypes) to unwind.

**Opportunities**
- No dominant modern OSS agile-PM for ERPNext yet.
- Frappe UI toolkit + Gameplan/Helpdesk/Insights precedents to learn from.
- Community contribution & services ecosystem.

**Threats**
- ERPNext upgrades breaking custom extensions (mitigated by upgrade-safe design).
- Scope creep toward re-cloning Jira (mitigated by reuse-first governance).
- Standalone Jira/Plane maturity; must not over-promise parity.

---

## 13. Functional Gap Analysis

Grouped by module, what functionally must be added vs. reused:

- **Planning:** Sprint/iteration lifecycle (plan → active → closed), backlog ordering, capacity — **new thin layer**; project/task CRUD, templates — **reuse**.
- **Execution:** modern board with statuses mapped to Task `status`/Workflow states, WIP limits, swimlanes, quick add, inline edit — **front-end build**; assignment, comments, attachments — **reuse**.
- **Estimation:** story points, estimate vs. actual (actual comes from Timesheet!) — **extend Task with fields**.
- **Hierarchy:** Epic/Story/Sub-task via Task `type` + `parent_task` — **reuse/extend, do not invent new hierarchy tables**.
- **Metrics:** velocity, burndown, burnup, CFD, cycle/lead time, workload — **build reports/charts** over Task + status-change history + Sprint membership.
- **Release:** version/release grouping + release notes/report — **extend (field or light doctype) + report**.
- **Views (Plane-like):** roadmap, timeline, modules, cycles, pages/docs — **front-end build**, docs可 reuse Frappe "Wiki"/"Web Page"/attachments or a light doctype.

## 14. Technical Gap Analysis

- **Status history for metrics:** burndown/cycle-time need timestamped status transitions. ERPNext Task has no native per-status history → **need a lightweight, append-only "Task Status Log"** (populated via a `on_update` doc-event) *or* reuse Frappe **Version** log parsing. Decision to be finalized in DB Design; leaning to a minimal status-log child/log doctype because Version parsing is fragile.
- **Sprint ↔ Task relationship:** many tasks to one active sprint → **link field (custom field) on Task** + a **Pulse Sprint** doctype. This is the *one* genuinely new master doctype justified by "no ERPNext equivalent."
- **Board performance:** rendering 100s of tasks needs a purpose-built API returning a lean payload; reuse `frappe.client`/`get_list` with field pruning rather than bespoke ORM.
- **Assignment hierarchy:** enforce via `permission_query_conditions` + a `validate` check on assignment, keyed to a role-rank map — **extension, no new engine**.
- **Front-end delivery:** choose ONE — (a) Frappe Desk Page + bundled JS, or (b) a Frappe UI (Vue) SPA served as a route (like Gameplan/Helpdesk). Recommendation in §19.
- **Upgrade safety:** all Task/Project additions as **Custom Fields via fixtures**, new doctypes in a dedicated Pulse module; **no edits to erpnext core**.

---

## 15. ERPNext Reuse Opportunities (principle)

Every Pulse feature maps to one of three buckets. The governing question for each: *"Does ERPNext/Frappe already do this?"* If yes → reuse. If almost → extend. Only a hard "no equivalent" earns a new component. §16–§18 enumerate the buckets.

## 16. Existing ERPNext Features to REUSE (as-is)

| Need | Reuse | Notes |
|---|---|---|
| Project container | **Project** | costing/billing/customer stay |
| Work item | **Task** (`parent_task`, `is_group`, `depends_on`, `type`, `priority`, `status`, `exp_start/end_date`, `%complete`) | the Pulse "card" IS a Task |
| Dependencies | **Task `depends_on` / Dependent Task** | no new dependency doctype |
| Time tracking / actuals | **Timesheet + Timesheet Detail** | "actual effort" = timesheet hours |
| Activity rates | **Activity Type / Activity Cost** | billing/costing rates |
| Repeatable structures | **Project Template / Project Template Task** | sprint/epic templates too |
| Status snapshots | **Project Update** | project health |
| Assignment | **ToDo / _assign (Assignment)** | "assignees" on a card |
| Discussion | **Comment / Communication** | task comments |
| History | **Activity Timeline / Version** | audit + potential metrics source |
| Files | **File / Attachments** | task attachments |
| Alerts | **Notification / Notification Settings / Email** | sprint/assignment alerts |
| Process | **Workflow / Workflow State/Action** | task & sprint transitions |
| Access | **Role / Role Profile / Permission / User Permission** | base RBAC |
| People | **User / Employee / Department** | members, capacity |
| Time-off | **Holiday List** | capacity/burndown working days |
| Money buckets | **Company / Cost Center / Customer** | financial dimensions |
| Reporting engine | **Report Builder / Query & Script Report / Dashboard Chart / Number Card** | build metrics on this, don't reinvent charts |
| Calendar | **Frappe Calendar view** | due dates |
| API | **Frappe REST / `@frappe.whitelist`** | no custom auth/session |

## 17. Existing ERPNext Features to EXTEND

| Extension | Mechanism | Why not new? |
|---|---|---|
| Story points, estimate | **Custom Field on Task** (Float/Select) | Task is the work item |
| Sprint link on task | **Custom Field on Task** → Link to Pulse Sprint | keep one task table |
| Epic / issue-type | **Task `type` (Task Type)** values or a Select custom field | hierarchy already exists |
| Release/version | **Custom Field on Task/Project** (+ optional light doctype) | grouping, not new work item |
| Backlog ordering | **Custom Field `pulse_rank` (Int/Float)** on Task | ordering is an attribute |
| Board columns | **Task `status` + Workflow States** | statuses already exist |
| Role hierarchy assignment | **`permission_query_conditions` + `validate` hook** | policy over existing perms |
| Kanban board defn | **reuse Frappe "Kanban Board" doctype** or extend | board config exists |
| Project agile settings | **Custom Fields on Project** (e.g., `enable_scrum`, default sprint length) | config on the container |

## 18. New Components Required (the *only* justified additions)

Kept deliberately minimal. Each must pass "no ERPNext equivalent."

| New component | Type | Justification |
|---|---|---|
| **Pulse Sprint** | Doctype (master) | No native iteration/time-box in ERPNext |
| **Pulse Task Status Log** | Doctype (append-only log) *(tentative)* | Timestamped transitions for burndown/cycle-time; Version parsing too fragile |
| **Pulse Settings** | Single doctype | App-level config (default sprint length, board defaults, role-rank map) — *may reuse/rename the existing one* |
| **Pulse UI** | Front-end (Desk Page or Frappe-UI SPA) | Board / Backlog / Roadmap / Rich Task / Sprint views |
| **Pulse metric reports** | Script/Query Reports + Dashboard Charts | Velocity, burndown, burnup, CFD, cycle/lead time, workload |
| **Fixtures** | Custom Fields, Roles, Workflows, Number Cards | Ship the extensions above reproducibly |

Everything else in the current build (Pulse Project, Pulse Task, Pulse Team, Pulse Milestone, Pulse Label, Pulse Task Dependency, Pulse Checklist Item, Pulse Project/Team Member) is **slated for retirement** in favor of ERPNext core + the small set above. Rationale per doctype:
- *Pulse Project → Project* (custom fields for agile flags).
- *Pulse Task → Task* (custom fields: story points, sprint, rank, type).
- *Pulse Milestone → Task with `is_milestone`/type* or Project Update.
- *Pulse Team/Team Member → Project Users / Role Profile / Department*; teams = ERPNext structures.
- *Pulse Label → tags (`_user_tags`) or existing "Tag"*; no new doctype.
- *Pulse Task Dependency → Task `depends_on`*.
- *Pulse Checklist Item → Task sub-tasks* or a simple checklist child on Task (extend, if truly needed).
- *Pulse Project/Team Member → Project User* child + assignment.

---

## 19. Recommended System Architecture

**Layered, reuse-first:**

```
┌─────────────────────────────────────────────────────────────┐
│  EXPERIENCE (Pulse)                                          │
│  Modern UI: Board · Backlog · Sprint · Roadmap · Rich Task   │
│  → Recommendation: Frappe UI (Vue) SPA on a portal route,    │
│    like Gameplan/Helpdesk (already in your bench).           │
└───────────────▲─────────────────────────────────────────────┘
                │ Frappe REST / whitelisted thin endpoints
┌───────────────┴─────────────────────────────────────────────┐
│  AGILE LAYER (Pulse — thin)                                  │
│  Pulse Sprint · Status Log · Settings · metric reports ·     │
│  doc-events (status log, rank) · permission hooks (hierarchy)│
└───────────────▲─────────────────────────────────────────────┘
                │ extends via Custom Fields + links
┌───────────────┴─────────────────────────────────────────────┐
│  SYSTEM OF RECORD (ERPNext core — unchanged)                 │
│  Project · Task · Timesheet · Activity Cost · Project Update │
│  Workflow · Assignment · Comments · Notifications · Reports  │
│  Company · Customer · Department · Cost Center · Holiday List │
└─────────────────────────────────────────────────────────────┘
```

**Front-end decision:** you already run **Gameplan, Helpdesk-style, Insights, Raven** on the other bench — all Frappe-UI SPAs. Recommend the **Frappe UI (Vue 3 + frappe-ui) SPA** approach for Pulse's modern views, calling thin whitelisted APIs, with the ERPNext Desk remaining available for finance/ops. This gives the Plane-grade UX without leaving the framework. (Alternative: Desk Page + bundled JS — lower ceiling on UX; not recommended for the roadmap/board ambition.)

**Back-end principle:** thin. Endpoints return lean board/backlog payloads; all writes go through standard `frappe.client`/document API so validations, permissions, and doc-events fire normally.

## 20. Development Philosophy

- **Extension-only, upgrade-safe:** fixtures for custom fields/roles/workflows; a dedicated module; zero core edits; no monkey-patching core doctypes.
- **Thin controllers, framework-first:** prefer doc-events, workflow, and permission hooks over service classes that reinvent framework behavior.
- **API contract stability:** version the whitelisted endpoints; keep them few and lean.
- **Test the extensions, not the framework:** unit-test Pulse logic (status log, hierarchy rule, metrics); trust Frappe for CRUD/permission internals.
- **Ship vertical slices:** each release delivers one usable workflow end-to-end.

## 21. UX Philosophy

- **Speed & focus:** board < 1s for 500 cards; keyboard-first; ≤2 clicks to common actions.
- **Progressive disclosure:** hide agile complexity until a project enables Scrum.
- **Familiar patterns:** Jira/Plane muscle memory (drag, quick-add, inline edit, command-k).
- **Consistency:** use frappe-ui components + a small Pulse design system; respect ERPNext theming.
- **Delight in the details:** empty states, optimistic updates, smooth DnD, clear sprint/burndown visuals.
- **Accessibility:** keyboard nav, contrast, ARIA on interactive board elements.

## 22. Database Philosophy

- **One work-item table:** Task. No shadow tables. Pulse adds *columns* (custom fields), not *tables*, wherever possible.
- **New tables only for genuinely new concepts:** Sprint, Status Log (tentative), Settings.
- **Normalize via links, not duplication:** Sprint↔Task by link field; never copy task data into Pulse rows.
- **Index for the board & metrics:** ensure indexes on Task `status`, `project`, sprint link, `pulse_rank`.
- **Append-only for history:** status log is write-once rows → clean burndown/cycle-time math.
- **Respect framework columns:** use `_assign`, `_user_tags`, `owner`, `modified` rather than parallel fields.

## 23. Coding Philosophy

- **PEP8 / Frappe conventions**; `frappe` APIs over raw SQL; parameterized queries only.
- **Least custom code:** if a hook, workflow, or setting can do it, don't write Python.
- **Permission-safe by default:** never `ignore_permissions=True` on user-triggered paths; whitelist deliberately.
- **Idempotent installs/migrations:** safe re-run; guard fixture creation.
- **Small, pure, tested functions** for metrics; docstrings explaining agile formulas.
- **Front-end:** typed, componentized Vue; central API client; no business logic duplicated from server.

## 24. Security Philosophy

- **Reuse Frappe auth/session/CSRF** — no custom auth.
- **RBAC via roles + permission levels**; hierarchy assignment enforced server-side (`validate` + `permission_query_conditions`), never only in UI.
- **Whitelist minimally;** validate every argument; enforce doc-level permission in each endpoint (`frappe.has_permission`).
- **User Permissions** for project/company scoping; respect existing restrictions.
- **No permission bypass** in APIs/services; audit via Frappe Version/timeline.
- **Field-level protection** for financial fields (permlevel) so delivery users can't edit costing.

## 25. Scalability Philosophy

- **Data:** thousands of tasks per project, hundreds of sprints — Task table already scales; keep queries indexed and paginated.
- **Board API:** cursor/limit pagination, field pruning, server-side filtering; avoid N+1 by batching.
- **Background work:** heavy metrics precomputed via scheduler into Dashboard Chart cache / a summary doctype, not computed per page load.
- **Multi-company / multi-team:** rely on ERPNext dimensions (Company, Cost Center) and User Permissions.
- **Horizontal:** standard Frappe multi-worker/Redis setup; no app-level state.

## 26. Performance Considerations

- Lean board payloads (only fields the card needs).
- Cache sprint/velocity aggregates (scheduler → cache/summary).
- Debounced drag persistence; optimistic UI with server reconcile.
- Indexes on hot columns (status, project, sprint, rank, `_assign` usage patterns).
- Avoid recomputing burndown on every render — snapshot daily via scheduled job.
- Lazy-load roadmap/timeline ranges; virtualize long lists.

## 27. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Re-cloning ERPNext (parallel doctypes) — *already occurred* | High | High | Reuse governance; retire Pulse* doctypes; Reuse Matrix gate |
| ERPNext upgrade breaks extensions | Med | High | Fixtures + custom fields + own module; CI against new ERPNext |
| Scope creep to full Jira parity | High | Med | MVP discipline; phase gates |
| UX under-delivers vs Plane | Med | High | Invest custom-code budget in front-end; use frappe-ui |
| Metrics need status history not present | High | Med | Status Log doctype from day one |
| Performance on large boards | Med | Med | Lean APIs, pagination, precomputed metrics |
| Maintainer bandwidth | Med | High | Minimize code; lean on framework; tests + docs |
| Data migration from current build | Med | Med | One-time migration script Pulse*→core (documented) |

## 28. Technical Challenges

- Capturing **timestamped status transitions** cleanly for burndown/cycle-time.
- **Drag-and-drop persistence** with ordering (`pulse_rank`) at scale without race conditions.
- **Mapping workflow states ↔ board columns ↔ Task status** coherently.
- **Actual effort from Timesheet** aggregated per task/sprint efficiently.
- **Role-hierarchy assignment** expressed as data (role-rank map) and enforced in query + validate.
- **SPA ↔ Desk coherence:** same permissions, same data, two front-ends.
- **Upgrade-safe fixtures** that don't collide with user customizations.

## 29. Business Challenges

- **Adoption:** convincing teams already on Jira/Plane to switch; requires real UX parity on core flows.
- **Positioning:** "not another project system" messaging so ERPNext admins trust it.
- **Support & docs** for an OSS project with limited maintainers.
- **Migration cost** for the existing (parallel) build's data.
- **Expectation management:** clear about what is *not* in MVP.

## 30. Development Strategy

1. **Re-baseline** on ERPNext core (retire parallel doctypes; keep name & any reusable UI).
2. **Extend** Task/Project via fixtures (story points, sprint link, rank, agile flags).
3. **Add** Pulse Sprint + Status Log + Settings (the only new tables).
4. **Build** the modern SPA views incrementally (Board → Backlog → Sprint → Roadmap → Rich Task).
5. **Add** metrics reports/charts (velocity, burndown, …).
6. **Harden**: permissions/hierarchy, performance, tests, docs.
7. **Migrate** existing data; release.

Each step is a vertical, shippable slice. Governance gate at each step: *"What did we reuse vs. build, and why?"* (feeds the Reuse Matrix doc).

## 31. MVP Strategy (v1.0)

**Goal:** a team can run a sprint on ERPNext data with a modern board — nothing more.

Includes: Custom fields (story points, sprint, rank, type) · **Pulse Sprint** · **Status Log** · **modern Board** (columns from Task status, drag, quick-add, inline edit, assignees via `_assign`) · **Backlog** (ordering, move-to-sprint) · **Sprint plan/active/close** · **Burndown + Velocity** (reuse chart engine) · reuse of assignment/comments/attachments/notifications · hierarchy assignment rule (basic). Financial integration inherited automatically because cards are Tasks.

Explicitly **out**: roadmap/timeline, modules/cycles-as-views, releases, advanced metrics (CFD, lead time), pages/docs, multi-board swimlanes/WIP polish.

## 32. Version 2 Strategy

- **Roadmap & Timeline** views (portfolio planning).
- **Epics** polish (Task type hierarchy + epic view) and **Releases/Versions** + release report.
- **Board polish:** swimlanes, WIP limits, saved filters/views.
- **More metrics:** burnup, cumulative flow, cycle/lead time, workload/capacity vs Holiday List.
- **Rich Task pane** parity with Plane (sub-tasks, checklist, links, activity in one view).
- **Workflow-driven transitions** configured via Frappe Workflow.

## 33. Version 3 Strategy

- **Modules & Cycles** (Plane-style) as first-class planning views.
- **Pages/Docs** per project (reuse Wiki/Web Page or light doctype).
- **Advanced dashboards & portfolio analytics**; forecasting from velocity.
- **Automations** (reuse Frappe Notification/Assignment Rule/Auto-repeat) surfaced in Pulse UI.
- **Plugin/extension points** for the community.
- **Mobile-optimized** experience / PWA.

## 34. Long-Term Vision

Pulse becomes the **de-facto agile delivery layer of ERPNext** — the "HRMS of project management": an official-quality app that any ERPNext shop installs to get modern delivery *and* keep finance. Deep but non-duplicative integration; a healthy contributor community; an extension marketplace.

## 35. Competitive Positioning

| | Jira | Plane | ERPNext Projects | **Pulse** |
|---|---|---|---|---|
| Agile depth | ★★★★★ | ★★★☆ | ★☆ | ★★★★ (target) |
| Modern UX | ★★★★ | ★★★★★ | ★★ | ★★★★ (target) |
| Financial/ERP integration | ★★ | ★ | ★★★★★ | ★★★★★ (inherited) |
| OSS / self-host | ⚠️ | ✅ | ✅ | ✅ |
| Single system w/ billing+delivery | ❌ | ❌ | ⚠️ | ✅ (unique) |

**One-line positioning:** *"Jira-grade agile + Plane-grade UX, natively financially integrated — because every card is an ERPNext Task."*

## 36. Similar Products Analysis (Frappe ecosystem to learn from)

- **Gameplan** (Frappe) — modern Vue SPA, teams/discussions/pages; reference for SPA architecture & UX. *(present in your other bench)*
- **Helpdesk** (Frappe) — frappe-ui SPA over doctypes; reference for board/list UX + API patterns.
- **Insights** — dashboards/analytics patterns for metrics.
- **Raven** — real-time patterns.
- **ERPNext HRMS** — reference for a large, official *extension* app done upgrade-safely.

Lesson: the successful modern Frappe apps are **SPAs over doctypes**, not parallel data models. Pulse should follow that shape.

## 37. Open Source Strategy

- Permissive/standard Frappe app license; public repo; clear README + docs site.
- **Clean install** (`bench get-app` → `bench install-app pulse`) with fixtures.
- Semantic versioning; changelog; ERPNext-version compatibility matrix.
- CI: lint + tests + install against target Frappe/ERPNext versions.
- Issue templates, roadmap in the open, "good first issue" labels.

## 38. Community Contribution Strategy

- **CONTRIBUTING.md**, coding standards (this doc's §23), PR review checklist including the *reuse gate*.
- Architecture docs (this set) so contributors don't reintroduce parallel doctypes.
- Discussion forum / chat; public roadmap; recognition for contributors.
- Good test coverage so external PRs are safe to merge.

## 39. Plugin / Extension Strategy

- **Stable whitelisted API** + documented doc-events for others to hook.
- **Settings-driven** behavior (Pulse Settings) so orgs configure without forking.
- Respect Frappe extension points (custom fields, workflows, notifications, client scripts) so customers customize Pulse the way they customize ERPNext.
- Reserve a **hooks surface** (e.g., events on sprint close, card move) for downstream apps.

## 40. Final Recommendations

1. **Proceed with Pulse — but re-baseline onto ERPNext core.** The vision is sound; the current implementation's parallel data model is the defect. Retire the `Pulse *` project/task doctypes.
2. **Adopt the three-layer architecture** (§19): ERPNext core (record) → thin Pulse agile layer → Frappe-UI SPA (experience).
3. **Spend the custom-code budget on the front-end and metrics,** not on re-implementing project/task/assignment/permission plumbing.
4. **Add only three tables** (Sprint, Status Log, Settings) and a set of Custom Fields — everything else reuses/extends.
5. **Enforce the reuse gate** in every future doc and PR: *"Does ERPNext already do this? Can we extend instead of build?"*
6. **Build the SPA like Gameplan/Helpdesk** (already proven in your bench) for Plane-grade UX inside Frappe.
7. **Plan a one-time migration** from the current build's data into core Task/Project.
8. **Ship the MVP narrowly** (§31): sprint + board + burndown/velocity on core data. Prove the model before expanding.

**Immediate next document:** proceed to **Document 1 — Project Overview**, then the PRD, then the **ERPNext Reuse Matrix** (elevated in priority — it is the contract that prevents re-cloning). A file-level defect list of the current build will be attached here as **Appendix A** once the code audit completes.

---

---

## Appendix A — File-Level Defects in the Current Build

*Result of a full code audit of `apps/pulse`. These are the concrete reasons the app "isn't working". They are catalogued for the migration plan; most disappear once Pulse is re-baselined onto ERPNext core (§18), but they confirm the diagnosis.*

**Scale of current custom code:** ~1,710 lines Python, ~106 lines JS, ~3,000+ lines DocType JSON, 10 doctypes. Nearly all of it is candidate for retirement under the reuse-first architecture.

### A1. Installation is broken (app won't install cleanly)
- `pulse/install.py` (~lines 61–62): loads the workspace from a **wrong path** — `.../workspace/pulse_workspace/pulse_workspace.json`, but the file is `.../workspace/pulse/pulse.json`. → **FileNotFoundError during `after_install`.** This alone blocks a clean install.
- `install.py` also hand-rebuilds the Workspace by parsing JSON and re-creating Number Cards — unnecessary; the workspace fixture should just ship as-is.
- `pulse/seed_data.py` (637 lines) is **never called** by any install hook (it's `if __name__ == "__main__"`), so a fresh install has no data.

### A2. The flagship "Pulse Board" doesn't exist
- `pulse/project_management/page/pulse_board/pulse_board.json` has **metadata only — no `.js`/`.html` implementation.** The workspace shortcut "Pulse Board" leads to a blank/404 page. The single most visible feature is non-functional.

### A3. ERPNext ↔ Pulse sync is broken (wrong field names)
- `pulse/hooks/doc_events/task.py` (~lines 36–39) reads ERPNext Task fields that don't exist: `exp_start_date`, `act_start_date`, `act_end_date`. ERPNext Task actually uses `exp_start_date`/`exp_end_date` and `act_start_date`/`act_end_date` on the core doctype — the mapping code targets the wrong names and **fails with AttributeError**, so bi-directional sync never completes. *(This bug is itself an argument for §18: if the card WERE the Task, there would be nothing to sync.)*

### A4. Destructive scheduled job
- `pulse/scheduled/overdue.py`: a **daily** job runs `UPDATE tabPulse Task SET status='In Progress' WHERE status NOT IN ('Done','Cancelled') AND expected_end_date < today()`. It silently overwrites user status changes every night, with no audit trail. Overdue should be a *derived indicator*, never a forced status write.

### A5. Systemic permission bypass (security flaw)
- **Every** write endpoint in `pulse/api/*.py` (`projects.py`, `tasks.py`, `teams.py`, `milestones.py`, `members.py`) uses `ignore_permissions=True`. Any authenticated user can create/modify/delete any project, task, team, or milestone regardless of role. The services layer is likewise permission-unaware.
- `pulse/hooks/permissions.py`: `has_team_permission()` **always returns True** — no team access control.
- `api/dashboard.py`: `get_task_counts_by_status()` and `get_recent_activity()` don't filter by project access → info disclosure across projects.
- This is exactly what the reuse-first model fixes for free: route writes through the standard document API and Frappe enforces roles/permissions automatically (§24).

### A6. Incomplete APIs
- Milestones API has only get/create — no update/delete. Teams API has only get/get-one/create — no update/delete. CRUD is half-built.

### A7. Duplicated logic / race risk
- Project task-count roll-up is computed in **both** `ProjectService.update_task_counts()` and `PulseTask.on_update()`; milestone progress duplicates the same pattern. Divergent counters and race conditions likely.

### A8. Minor
- `pulse_task.json` uses `autoname: hash` with a separately generated `task_key` — naming intent unclear.
- `pulse.bundle.js` is a 10-line stub.

**Net:** the DocType/service *structure* is tidy, but the app is blocked by an install crash, a missing flagship page, broken sync, a destructive job, and a systemic permission bypass — on top of the strategic problem that the whole data model is a parallel copy of ERPNext Projects. Re-baselining (§30) resolves the strategic problem and eliminates the majority of these defects by construction.

---

## Appendix B — "PMO" Rename Checklist (name = **Pulse** everywhere)

The working name leaked into the code as **"Project Management Office"**. To keep it **Pulse** everywhere:

| Location | Current | Change to |
|---|---|---|
| `pulse/hooks/__init__.py` → `app_title` | `"Project Management Office"` | `"Pulse"` |
| Module name `Project Management` (`modules.txt`, all doctype `module` fields, workspace `module`) | `Project Management` | `Pulse` *(rename module to match the brand; optional but recommended for consistency)* |
| Any UI labels / page titles / README referencing PMO or "Project Management Office" | — | `Pulse` |
| App description / `app_publisher` docs | — | `Pulse` |

Note: `app_name` is already `pulse` and `app_title` is the user-facing string — updating `app_title` to "Pulse" is the key change. Renaming the *module* from "Project Management" to "Pulse" is a larger operation (touches every doctype's `module` and the folder path) — defer to the re-baseline/migration step so it's done once, cleanly.

---

*End of Document 0. Awaiting approval to proceed to Document 1 (Project Overview).*
