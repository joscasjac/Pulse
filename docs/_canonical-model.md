# Pulse — Canonical Model & Charter (SINGLE SOURCE OF TRUTH)

> Every Pulse document and every line of code MUST conform to this file. If a change needs to deviate, update this file first. This exists so the project never contradicts itself.
>
> **Supersedes the archived 21-document set** (`docs/archive/`), which described a now-abandoned "reuse ERPNext" architecture. Re-baselined **2026-07-06**.

App name: **Pulse**. App id: `pulse`. Module: **Pulse**. Stack: **Frappe v16** (framework only).

---

## 1. The central decision: Pulse is STANDALONE and PLUG-AND-PLAY

Pulse is a self-contained agile project-management app combining the feature sets of **Plane** and **Jira**. It:

1. **Installs on ANY Frappe instance** via `bench get-app pulse && bench install-app pulse` with **zero dependency on ERPNext or any other app.** Only the Frappe framework is required.
2. **Owns 100% of its data.** No Pulse doctype links to any non-Pulse doctype **except** these Frappe-framework core doctypes: `User`, `Role`, `DocType`, `Workflow State`, `File`, `ToDo`, `Comment`, `Notification`. Never `Project`, `Task`, `Task Type`, `Timesheet`, `Employee`, `Customer`, `Company`, `Cost Center`, `Fiscal Year`, `Holiday List`, or any other ERPNext/HR doctype.
3. **Presents a modern Vue 3 SPA** (frappe-ui) at `/pulse`. Per-user customizable interactive dashboards; admins assign work; users tailor their own views.

**Governing rule (replaces the old one): Build Pulse-native → reuse ONLY framework primitives (auth, permissions, workflow, REST, notifications, files) → never depend on another business app.**

### Allowed framework-core links (the ONLY non-`Pulse` links permitted)
`User`, `Role`, `DocType`, `Workflow State`, `File`, `ToDo`, `Comment`, `Notification`. Anything else must be a `Pulse *` doctype or a Select/Data field.

---

## 2. Data model — Pulse-native doctypes (the system of record)

All in module **Pulse**, all prefixed `Pulse `. Current inventory (hardened in Phase 1):

**Core PM:** Pulse Project, Pulse Task, Pulse Sprint, Pulse Task Status Log, Pulse Issue Type, Pulse Label, Pulse Dependency, Pulse Checklist, Pulse Comment, Pulse Activity Log, Pulse Notification, Pulse Favorite, Pulse Saved Filter.

**People & org:** Pulse Team, Pulse Team Member, Pulse Project User, Pulse Role Rank, Pulse Allocation, Pulse Leave, Pulse Holiday List, Pulse Holiday.

**Time:** Pulse Timesheet, Pulse Timesheet Entry.

**Portfolio & planning:** Pulse Portfolio, Pulse Portfolio Project.

**OKRs:** Pulse Objective, Pulse Key Result, Pulse Key Result Project, Pulse OKR Check-in, Pulse Goal.

**Risk & governance:** Pulse Risk, Pulse Risk Action, Pulse Risk Task, Pulse Change Request, Pulse CR Approval, Pulse CR Task, Pulse Decision, Pulse Health Check.

**Meetings & retros:** Pulse Meeting, Pulse Meeting Attendee, Pulse Meeting Action, Pulse Meeting Decision, Pulse Retrospective, Pulse Retro Item, Pulse Retro Action, Pulse Retro Participant.

**Docs & config:** Pulse Document, Pulse Settings (Single).

**Dashboards (Phase 2):** Pulse Dashboard, Pulse Dashboard Widget — persist per-user customizable layouts.

> Naming: doctypes `Pulse <Thing>`; child tables `Pulse <Thing>`; fields `snake_case`. No `pulse_` custom-field prefix is needed anymore because Pulse owns its doctypes outright (that prefix belonged to the old extend-ERPNext approach).

---

## 3. Issue types (was ERPNext "Task Type")

**Pulse Issue Type** doctype (standalone). Seeded defaults: Epic, Story, Bug, Task, Sub-task, Improvement, Incident, Feature — each with color, optional icon, `is_epic`/`is_subtask` flags. `Pulse Task.task_type` links here. **Never** ERPNext `Task Type`.

---

## 4. Statuses & workflow

Board columns and agile statuses are Pulse-native (Select/state on Pulse Task + Pulse Task Status Log for history), driven by framework **Workflow / Workflow State** where gating is needed. Pulse Task Status Log is the append-only source for burndown, burnup, CFD, cycle/lead time.

---

## 5. Roles & hierarchical assignment

Roles (fixtures): `Pulse Admin`, `Pulse Manager`, `Pulse Team Lead`, `Pulse Senior Developer`, `Pulse Junior Developer`, `Pulse Intern`, `Pulse Viewer`. Ranks in **Pulse Role Rank** (child of Pulse Settings): Admin 100 → Manager 80 → Team Lead 60 → Senior Dev 40 → Junior Dev 20 → Intern 10 → Viewer 0.

Rule: a user may assign work only to users whose max rank ≤ their own (assign down/sideways, never up), enforced server-side. Admins/Managers assign tasks to anyone at or below their rank.

---

## 6. Reports, charts, dashboards

Metrics reports (Velocity, Burndown, Burnup, Cumulative Flow, Cycle Time, Lead Time, Workload, Sprint Report) all query **Pulse** doctypes only. Actual effort comes from **Pulse Timesheet**, never a hand-entered field and never ERPNext Timesheet.

Interactive dashboards (Phase 5) are per-user: a draggable/resizable widget grid persisted in **Pulse Dashboard / Pulse Dashboard Widget**, with admin-set default layouts.

---

## 7. Front-end plan

- **Target:** Vue 3 + **frappe-ui** SPA at `/pulse` (pattern: Frappe Helpdesk / Gameplan). Board (drag-drop, WIP, swimlanes), Backlog, Sprint, Rich Task pane, My Work, customizable Dashboards, plus Portfolio/OKR/Risk/Meeting/Retro/Docs modules.
- **Current (to be retired):** ~20 hand-built Desk Pages + `public/js/pulse_global.js` + `public/css/pulse.css`. Kept only until the SPA reaches parity, then removed.
- **API:** thin whitelisted endpoints in a single `pulse.api.*` namespace. Writes go through the standard document API so permissions/validations fire — no blanket `ignore_permissions=True`.

---

## 8. Install / packaging invariants (plug-and-play)

- **No `required_apps`** entry that forces ERPNext.
- `after_install` / `after_migrate` are **idempotent** and seed only Pulse-native masters (roles, issue types, workflow states, role ranks).
- Fixtures ship only `Pulse *` records + Pulse roles. No ERPNext-doctype fixtures.
- Demo data lives in a single optional seeder, never auto-run on install.
- **Exit test for "plug-and-play": `bench install-app pulse` succeeds on a Frappe site with ERPNext NOT installed.**

---

## 9. Phase roadmap (authoritative)

- **Phase 0 — Foundation reset & decoupling:** rewrite this charter; archive old docs; remove all ERPNext coupling (Task Type→Pulse Issue Type, Holiday List→Pulse Holiday List, Fiscal Year→Data); consolidate the two `api/` folders; remove root dev cruft. **Exit: installs on bare Frappe.**
- **Phase 1 — Data model hardening:** audit all doctypes for internal-only links, naming, indexes, permissions; finalize roles + hierarchical assignment.
- **Phase 2 — Clean backend API + dashboard persistence:** single `pulse.api.*`; Pulse Dashboard / Pulse Dashboard Widget.
- **Phase 3 — Vue SPA scaffold (frappe-ui):** `frontend/`, routing at `/pulse`, session auth, app shell.
- **Phase 4 — Core PM in SPA:** Board, Backlog, Sprint, Rich Task, My Work, task assignment.
- **Phase 5 — Customizable dashboards:** per-user widget grid + admin defaults.
- **Phase 6 — Advanced modules in SPA:** OKR, Risk, Meeting, Portfolio, Change Request, Retro, Docs, Timesheet, Roadmap, Resources, Intelligence.
- **Phase 7 — Packaging & plug-and-play validation:** idempotent install/migrate, optional demo data, tests, regenerated docs, fresh-bench install test, release 1.0.

---

## 10. Naming & conventions

- Doctypes: `Pulse <Thing>`. Module: `Pulse`. App: `pulse`. Roles: `Pulse <Role>`.
- API namespace: `pulse.api.*` (thin; standard document API for writes).
- No core-file edits, no monkey-patching; all via the app's own doctypes/hooks/fixtures. Upgrade-safe.
- The ONLY non-`Pulse` doctype links allowed are the framework-core set in §1.
