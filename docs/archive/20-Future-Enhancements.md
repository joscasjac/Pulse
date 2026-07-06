# Pulse — Future Enhancements

**Document 20 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26 · App `pulse` · Module `Pulse`
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new. Every future idea below is first checked against existing ERPNext/Frappe capability; the "Reuse" column records what we lean on.

---

## 0. How to read this backlog

This is the **v2/v3+ idea backlog** — beyond the Phase 1 MVP (Doc 15). Items are grouped by theme, prioritized (**P1** = next, **P2** = later, **P3** = opportunistic), sized (S/M/L), and mapped to the phase roadmap in `_canonical-model.md` §10 (Phase 2 = Modern Experience; Phase 3 = Portfolio & Ecosystem). Nothing here reopens the settled decisions: the card stays an ERPNext **Task**, and only the four canonical doctypes exist unless this backlog item explicitly updates the canonical model.

**Prioritization principles:** (1) highest UX leverage first (analysis §21); (2) prefer items with strong ERPNext reuse; (3) avoid scope creep toward full Jira clone (analysis §27); (4) each item ships as a vertical slice.

---

## 1. Views & planning (Plane-inspired)

| # | Idea | Priority | Phase | Size | ERPNext reuse |
|---|---|---|---|---|---|
| F1 | **Roadmap / Timeline view** — portfolio-level visual planning over Task dates + Sprint. | P1 | 3 | L | Enhance Frappe **Gantt** data; Task `exp_start/end_date` |
| F2 | **Modules & Cycles (Plane)** — Cycles = time-boxes, Modules = feature groupings, as first-class views. | P2 | 3 | L | **Cycles reuse Pulse Sprint**; Modules via Task Type/field — no new work-item table |
| F3 | **Releases + release report** — version grouping + generated release notes. | P1 | 3 | M | `pulse_release` field → optional light Release doctype; **Query/Script Report** + print format |
| F4 | **Pages / Docs per project** — attach living docs to a project. | P2 | 3 | M | Reuse Frappe **Wiki / Web Page / File**, or a light doctype only if needed |
| F5 | **Saved views / filters** across board, backlog, roadmap. | P2 | 2 | M | Reuse Frappe list-view filters / user settings |

---

## 2. AI features

| # | Idea | Priority | Phase | Size | Reuse / notes |
|---|---|---|---|---|---|
| F6 | **Auto-estimation** — suggest story points from task text + historical velocity. | P2 | 3 | M | Trained on Pulse Task Status Log + `pulse_story_points` history |
| F7 | **Summarization** — summarize a task's comments/activity or a sprint. | P2 | 3 | S | Over **Comment/Communication** timeline; no new store |
| F8 | **Standup digest** — auto-generated daily/standup summary (what moved, blockers, at-risk). | P1 | 3 | M | Derived from Status Log + `_assign`; delivered via Frappe **Notification/Email** |
| F9 | **Smart triage** — suggest assignee (respecting rank rule) / Task Type / priority. | P3 | 3 | M | Must honor hierarchical-assignment rule (canonical §6) |

> AI features are additive and opt-in; they read core data and never bypass permissions. Provider/model choices are deferred to implementation.

---

## 3. Integrations

| # | Idea | Priority | Phase | Size | Reuse / notes |
|---|---|---|---|---|---|
| F10 | **GitHub / GitLab issue sync** — two-way link issues ↔ Task. | P1 | 3 | L | Map to Task; store external ref in a `pulse_*` field; webhooks via Frappe |
| F11 | **Git commit / PR linking** — reference `TASK-123` in commits; show commits on the task. | P2 | 3 | M | Webhook → Comment/Communication on the Task |
| F12 | **CI/CD status** — surface build/deploy status on tasks/releases. | P3 | 3 | M | Webhooks → task/release; reuse Notification |
| F13 | **Slack / chat** — sprint & assignment alerts, card actions. | P2 | 3 | M | Prefer **Raven** patterns; reuse Frappe Notification channels |
| F14 | **Calendar sync** — due dates / sprint dates to external calendars. | P2 | 3 | S | Reuse Frappe **Calendar** + iCal export |

---

## 4. Portfolio, resource & capacity

| # | Idea | Priority | Phase | Size | ERPNext reuse |
|---|---|---|---|---|---|
| F15 | **Portfolio dashboards** — cross-project health, velocity, margin. | P1 | 3 | M | **Dashboard Chart / Number Card / Report**; margin from Project costing |
| F16 | **Resource / capacity planning** — allocation vs. availability. | P2 | 3 | L | **Employee / Department / Holiday List**; `_assign` + story points |
| F17 | **Velocity forecasting** — project completion from historical velocity. | P2 | 3 | M | Pure function over sprint velocity history |
| F18 | **Workload balancing** — open points per assignee, rebalance suggestions. | P2 | 3 | M | `_assign` + `pulse_story_points`; reuse reporting |

---

## 5. Process depth (Jira-inspired)

| # | Idea | Priority | Phase | Size | Reuse / notes |
|---|---|---|---|---|---|
| F19 | **Workflow-driven transitions** with conditions/validators/post-functions. | P1 | 2 | M | Reuse Frappe **Workflow** conditions/actions — configure, don't code |
| F20 | **Board polish** — WIP limits, swimlanes. | P1 | 2 | M | Front-end over Task `workflow_state` |
| F21 | **OKRs** — objectives/key-results linked to projects/epics. | P3 | 3+ | L | Light doctype only if no reuse; link to Project/Task |
| F22 | **Advanced metrics** — CFD, cycle/lead time, control charts. | P1 | 2 | M | Built on **Status Log** + reporting engine |
| F23 | **Automations UI** — surface Frappe Assignment Rule / Auto-repeat / Notification. | P2 | 3 | M | Reuse framework automations; Pulse just surfaces them |

---

## 6. Platform & ecosystem

| # | Idea | Priority | Phase | Size | Reuse / notes |
|---|---|---|---|---|---|
| F24 | **Mobile / PWA** — mobile-optimized SPA. | P2 | 3 | L | frappe-ui responsive; PWA shell |
| F25 | **Plugin / extension API** — stable whitelisted API + documented doc-events (sprint close, card move) for downstream apps. | P1 | 3 | M | Contract over existing hooks; canonical §11 |
| F26 | **Extension marketplace** — community plugins/templates. | P3 | 3+ | L | Depends on F25 |
| F27 | **Community roadmap** — public, votable roadmap. | P2 | ongoing | S | Reuse GitHub Projects / discussions; dogfood Pulse itself |
| F28 | **Project templates gallery** — shareable sprint/epic templates. | P2 | 3 | M | Reuse **Project Template / Project Template Task** |

---

## 7. Prioritized shortlist (what to do first after MVP)

Ordered by leverage × reuse × phase-fit:

1. **F19 Workflow-driven transitions** (P1, Phase 2) — configuration over code; high control, near-zero build.
2. **F20 Board polish (WIP/swimlanes)** + **F22 Advanced metrics (CFD/cycle time)** (P1, Phase 2) — completes the modern board using Status Log we already log.
3. **F1 Roadmap/Timeline** (P1, Phase 3) — biggest portfolio-planning gap; reuses Gantt.
4. **F3 Releases + report** (P1, Phase 3) — small extend + report; high user value.
5. **F15 Portfolio dashboards** (P1, Phase 3) — pure reporting-engine reuse; surfaces margin (the ERP differentiator).
6. **F10 GitHub/GitLab sync** + **F8 Standup digest** (P1) — top integration/AI asks; both map onto core Task + Notifications.
7. **F25 Plugin API** (P1, Phase 3) — unlocks community contribution (analysis §39).

Everything else is P2/P3, pulled forward only if it stays reuse-first and doesn't drift toward re-cloning Jira/Plane.

---

## 8. Reuse-first reminders for every future item

- The card is always a **Task**; the project is always a **Project**. No new work-item table — ever.
- Prefer **custom fields, Task Type, Workflow, fixtures, reports, and framework automations** before writing Python or adding a doctype.
- Any new doctype requires updating `_canonical-model.md` first (currently only Sprint, Task Status Log, Settings, Role Rank exist).
- Actuals/costs/margin always come from **Timesheet / Project costing** — never hand-entered.
- New surfaces must honor permissions and the hierarchical-assignment rule server-side.

*End of Document 20.*
