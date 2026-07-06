# Pulse — UI/UX Specification

**Document 8 of 21 · Experience Design (UI/UX)**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe **v16.25** · ERPNext **v16.26**
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).
**Front-end phasing:** Phase 1 reuses Frappe Kanban Board + Desk workspace + Gantt/Calendar; Phase 2 introduces the frappe-ui (Vue 3) SPA at `/pulse`; Phase 3 adds portfolio views.

> This document specifies *how Pulse looks and behaves*. It inherits every decision from Document 0 (Enterprise Analysis) and `_canonical-model.md`. The central UX consequence of the canonical model: **every card the user drags is an ERPNext Task, every board column is a Frappe Workflow state, every "actual hours" number comes from a Timesheet.** The UI never invents data — it renders core data beautifully.

---

## Table of contents

1. UX Principles
2. Design System (colors, typography, spacing, components, tokens, iconography)
3. Information Architecture & Navigation
4. Screen-by-Screen Specifications
5. Interaction Patterns
6. Empty / Loading / Error State Guidance
7. Responsive, Mobile & Accessibility
8. Phase 1 (Desk/Kanban reuse) ↔ Phase 2 (SPA) Mapping

---

## 1. UX Principles

Pulse must feel as fast and modern as Plane/Jira while running inside Frappe. Seven principles govern every screen.

### P1 — Speed is the feature
- Board renders **< 1s for 500 tasks** (Objective O2). Achieved via lean board payloads (only card fields), server-side filtering, virtualization of long lists, and precomputed metrics.
- **Optimistic UI everywhere:** drag, inline edit, quick-add, and status change render instantly and reconcile with the server in the background; on failure they roll back with a toast.
- Perceived performance beats raw performance: skeletons on first paint, never a blank spinner-only screen.

### P2 — Progressive disclosure
- A 3-person team sees Projects, Board, and Task detail. Agile machinery (Sprints, Story Points, Velocity, Burndown, Backlog rank) appears **only when the project enables Scrum** (`pulse_enable_scrum`).
- Kanban-only projects never see Sprint/Backlog/Velocity nav items.
- The Rich Task pane reveals depth top-to-bottom: title + status first; sub-tasks, checklist, dependencies, time log, activity collapse below the fold.

### P3 — Familiar Jira/Plane muscle memory
- Drag-and-drop cards; **quick-add** at the bottom of a column/list; **inline edit** of title/assignee/points; **Command-K** palette; keyboard shortcuts for create/assign/move.
- Card anatomy mirrors Jira: `KEY-123`, title, type icon, assignee avatar, story-point pill, labels.
- No new mental model to learn — Pulse borrows patterns users already know.

### P4 — Keyboard-first
- Every primary action has a shortcut (see §5.5). Command-K reaches any project, task, or action.
- Focus rings are always visible; Tab order is logical; the board is fully operable without a mouse (arrow keys move focus between cards/columns; `Space`+arrows move a card).

### P5 — Consistency with frappe-ui
- Phase 2 uses **frappe-ui** components (`Button`, `Dialog`, `Autocomplete`, `Dropdown`, `Badge`, `Avatar`, `ListView`, `Tabs`, `TextInput`, `FormControl`, `Tooltip`, `Toast`, `Breadcrumbs`, `FeatherIcon`). Pulse adds a thin design-token layer on top — no bespoke component that frappe-ui already provides.
- Phase 1 respects ERPNext Desk theming and controls so the two experiences feel coherent (same permissions, same data, two front-ends).

### P6 — Delight in the details
- Beautiful, actionable **empty states** (illustration + one-line explanation + primary CTA).
- Smooth 150–200 ms drag/drop and pane transitions; subtle elevation on card hover; confetti-free but satisfying sprint-complete summary.
- Clear sprint/burndown visuals with legends and "ideal vs actual" lines.

### P7 — Accessibility & trust
- WCAG 2.1 AA: text contrast ≥ 4.5:1, non-text/UI contrast ≥ 3:1, status color never the *only* signal (icon + label back it up).
- ARIA roles on the board (`role="list"`/`listitem`, `aria-grabbed`, live regions for DnD announcements).
- Respect `prefers-reduced-motion`; honor Frappe's light/dark theme.
- Server-side permission enforcement is always the source of truth — the UI hides what a user can't do, but never *relies* on hiding for security (§24 of Doc 0).

---

## 2. Design System

Pulse's design system is a **thin token layer over frappe-ui / ERPNext Desk**, not a from-scratch system. It defines semantic tokens (status, priority, type) and reuses frappe-ui's base palette, spacing, and components.

### 2.1 Color palette

Base neutrals and brand come from frappe-ui's Tailwind palette; Pulse fixes semantic tokens on top.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--pulse-bg` | `#FFFFFF` | `#1C1C1F` | app background |
| `--pulse-surface` | `#F9FAFB` (gray-50) | `#232326` | column / card wells |
| `--pulse-card` | `#FFFFFF` | `#2A2A2E` | card face |
| `--pulse-border` | `#E5E7EB` (gray-200) | `#3A3A3E` | dividers, card border |
| `--pulse-text` | `#1F272E` (gray-900) | `#F3F4F6` | primary text |
| `--pulse-text-muted` | `#687076` (gray-600) | `#A1A1AA` | secondary text |
| `--pulse-primary` | `#2490EF` (Frappe blue-500) | `#4AA3F0` | primary actions, links, focus |
| `--pulse-primary-hover` | `#1786E0` | `#2490EF` | hover state |
| `--pulse-focus-ring` | `#2490EF` @ 40% | same | keyboard focus |

Pulse **inherits Frappe's blue** as primary so the SPA and Desk feel like one product.

### 2.2 Status color tokens (board columns / workflow states)

Statuses come from the **Pulse Task Workflow** (§5 canonical). Each state has a fixed token; color is *supplementary* to the label + icon.

| Workflow state | Token | Light hex | Icon |
|---|---|---|---|
| `Backlog` | `--status-backlog` | `#8B8B8B` gray | `inbox` |
| `To Do` | `--status-todo` | `#687076` slate | `circle` |
| `In Progress` | `--status-progress` | `#2490EF` blue | `loader` (spin on hover) |
| `In Review` | `--status-review` | `#F5A623` amber | `eye` |
| `Done` | `--status-done` | `#28A745` green | `check-circle` |
| `Cancelled` | `--status-cancelled` | `#CB2929` red | `x-circle` |

### 2.3 Priority color tokens (Task `priority`)

Reuses ERPNext Task `priority` values (Low / Medium / High / Urgent).

| Priority | Token | Hex | Icon |
|---|---|---|---|
| Urgent | `--prio-urgent` | `#CB2929` red | `chevrons-up` |
| High | `--prio-high` | `#F5A623` amber | `chevron-up` |
| Medium | `--prio-medium` | `#2490EF` blue | `minus` |
| Low | `--prio-low` | `#687076` gray | `chevron-down` |

### 2.4 Task-type tokens (Task Type fixtures)

Type semantics come from **Task Type** (`Epic`, `Story`, `Bug`, `Task`, `Sub-task`, `Improvement`, `Incident`, `Feature`).

| Type | Icon | Color |
|---|---|---|
| Epic | `zap` | purple `#8250DF` |
| Story | `bookmark` | green `#28A745` |
| Bug | `alert-octagon` | red `#CB2929` |
| Task | `check-square` | blue `#2490EF` |
| Sub-task | `git-branch` | gray `#687076` |
| Improvement | `trending-up` | teal `#0EA5A5` |
| Incident | `alert-triangle` | orange `#F5580C` |
| Feature | `star` | indigo `#4F46E5` |

### 2.5 Typography

Reuse frappe-ui's font stack (Inter). Scale:

| Role | Size / weight | Use |
|---|---|---|
| Display | 24px / 600 | screen titles |
| H1 | 20px / 600 | pane titles, section headers |
| H2 | 16px / 600 | column headers, card group titles |
| Body | 14px / 400 | default text, card titles |
| Body-strong | 14px / 500 | labels, active nav |
| Small | 12px / 400 | metadata, timestamps, points |
| Mono | 12px / 500 (Menlo/ui-mono) | task keys `PLS-123` |

Line-height 1.5 body, 1.3 headings. Max content width 1440px; task pane reading column max 720px.

### 2.6 Spacing, radius, elevation

- **Spacing scale (4px base):** 4 / 8 / 12 / 16 / 24 / 32 / 48.
- **Card padding:** 12px; **column gutter:** 12px; **page padding:** 24px (16px mobile).
- **Radius:** 6px cards/inputs, 8px panes/modals, 999px pills/avatars.
- **Elevation:** cards flat with 1px border; on drag → shadow `0 4px 12px rgba(0,0,0,.12)`; modals `0 8px 32px rgba(0,0,0,.16)`.

### 2.7 Component library (frappe-ui, reused)

| Pulse element | frappe-ui component | Notes |
|---|---|---|
| Buttons | `Button` (variants: solid/subtle/ghost/outline) | primary = solid blue |
| Modals / panes | `Dialog`, side-`Drawer` | Rich Task pane = right drawer or modal |
| Menus | `Dropdown`, `Popover` | context menus, filters |
| People pickers | `Avatar`, `Autocomplete` (users) | assignee selection |
| Chips | `Badge` | status, priority, labels, points |
| Lists | `ListView` | Backlog, My Work |
| Tabs | `Tabs` | task pane sections, reports |
| Inputs | `TextInput`, `Textarea`, `FormControl`, `Select` | inline + forms |
| Rich text | frappe-ui editor (TipTap) | task description, comments |
| Command palette | `Command`/custom over `Dialog` | Command-K |
| Toasts | `toast()` | optimistic success/error |
| Breadcrumbs | `Breadcrumbs` | workspace → project → view |
| Icons | `FeatherIcon` (lucide/feather set) | see §2.4 |

**Phase 1** uses the equivalent Desk controls (Kanban Board, `frappe.ui.form`, ListView, Report view) rather than frappe-ui.

### 2.8 Iconography

Single icon family: **Feather/Lucide** (frappe-ui default). Status, priority, and type icons are enumerated above. Rules: 16px in cards, 20px in nav, stroke 1.5px, always paired with a text label or `aria-label`.

---

## 3. Information Architecture & Navigation

### 3.1 Two front doors (by phase)

- **Phase 1:** a Desk **Pulse workspace** (left-sidebar workspace like ERPNext modules) with shortcuts to Kanban Board, Task list, Gantt, Calendar, Sprint list, and metric reports.
- **Phase 2+:** the **Pulse SPA at `/pulse`** with the full left-nav below. Desk remains available for finance/ops.

### 3.2 SPA global layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ [Pulse ▾ workspace]   ⌘K Search…            [+ Create ▾]  [🔔] [avatar]│  top bar
├───────────────┬──────────────────────────────────────────────────────┤
│ LEFT NAV      │  BREADCRUMB: Workspace / Website Revamp / Board       │
│               │  ┌────────────────────────────────────────────────┐  │
│ ⌂ My Work     │  │                                                │  │
│ ▤ Projects    │  │          MAIN CONTENT AREA                      │  │
│   › Website   │  │  (Board / Backlog / Sprint / Roadmap / …)      │  │
│   › Mobile    │  │                                                │  │
│ ── project ──│  │                                                │  │
│ ▦ Board       │  │                                                │  │
│ ≣ Backlog     │  │                                                │  │
│ ↻ Sprints     │  │                                                │  │
│ ⤳ Roadmap     │  │                                                │  │
│ ◫ Epics       │  │                                                │  │
│ ▤ Reports     │  └────────────────────────────────────────────────┘  │
│ ⚙ Settings    │                                                       │
└───────────────┴──────────────────────────────────────────────────────┘
```

### 3.3 Left navigation

Two tiers: **workspace-level** (always visible) and **project-level** (visible when a project is selected).

- **Workspace-level:** `My Work` (⌂), `Projects` (▤, expandable tree), `Reports` (portfolio), `Settings` (Pulse Settings).
- **Project-level** (contextual, only for the active project): `Board`, `Backlog`*, `Sprints`*, `Roadmap`†, `Epics`†, `Reports`, `Project Settings`.
  - *`Backlog` and `Sprints` appear only when `pulse_enable_scrum = 1` (progressive disclosure, P2).
  - †`Roadmap` and `Epics` are Phase 3 / Phase 2 respectively.

### 3.4 Breadcrumbs

Every screen shows `Workspace / <Project> / <View>` (frappe-ui `Breadcrumbs`). Task pane appends `/ <KEY-123>`. Each crumb is a link; the project crumb opens a project switcher dropdown.

### 3.5 Command-K palette

- Trigger: `⌘/Ctrl+K`. A `Dialog` with fuzzy search over: projects, tasks (by key/title), sprints, actions ("Create Task", "Go to Backlog", "Start Sprint"), and recent items.
- Results grouped: **Actions** · **Tasks** · **Projects** · **Recent**.
- Arrow keys navigate, Enter executes, Esc closes. Type `>` to filter to actions only, `#` to search tasks only.

### 3.6 Global "+ Create"

Top-bar dropdown and shortcut `C`: Create Task (default), Sprint, Project, Epic. Opens quick-create dialog scoped to the current project.

---

## 4. Screen-by-Screen Specifications

Each screen lists: **Purpose · Layout · Key components · Interactions · States · Data · Phase.**

> Data-source note applies to all screens: cards = **Task**, columns = **Workflow state** (`workflow_state`), assignees = `_assign`, points = `pulse_story_points`, rank = `pulse_rank`, sprint = `pulse_sprint`, actual hours = **Timesheet**, comments/attachments/activity = Frappe framework. The UI is a lens over core data.

---

### 4.1 Dashboard / My Work

**Purpose.** A personal home: everything assigned to me across projects, what's due, what's in my active sprint, and quick access to recent work.

**Layout.**
```
┌ My Work ─────────────────────────────────────────────────────────┐
│ Good morning, Priya.                             [ This sprint ▾ ] │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│ │ Assigned │ │ Due today│ │ In review│ │  Points  │  number cards│
│ │    12    │ │    3     │ │    2     │ │  8 / 21  │              │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│ ── My Tasks ─────────────────────────  [ Board | List ]  filters │
│ ▸ To Do (4)                                                       │
│   □ PLS-14  Fix login redirect        ●High  ◷Due Tue   ◆3       │
│   □ PLS-22  Update onboarding copy     ○Med             ◆2       │
│ ▸ In Progress (3)  …                                              │
│ ── Recent ── · ── Mentions & Comments ──                          │
└───────────────────────────────────────────────────────────────────┘
```

**Key components.** Number cards (Assigned, Due today, In review, Sprint points done/total); grouped task list (by status) or personal board toggle; Recent items rail; Mentions/comments feed (from Frappe Notification/Comment).

**Interactions.** Click a task → Rich Task pane. Inline status change via the checkbox/status pill. Filter (project, priority, due). Toggle Board/List. "This sprint / All open / Overdue" scope selector.

**States.**
- *Empty:* "No work assigned to you yet." + illustration + "Browse projects" CTA.
- *Loading:* skeleton number cards + 4 shimmer rows.
- *Error:* inline banner "Couldn't load your work. Retry."

**Data.** `_assign` contains current user; joins Task (key/title/priority/due/points/status), active `pulse_sprint`, Frappe notifications.

**Phase.** **P1:** ERPNext "Assigned To Me" list + workspace Number Cards. **P2:** dedicated SPA My Work with personal board.

---

### 4.2 Board (Kanban)

**Purpose.** The flagship execution view. Move work across workflow states by dragging cards.

**Layout.**
```
┌ Website Revamp · Board ──────────────  [Sprint 4 ▾] [Filter] [⋯] [+]┐
│ Group by: Status ▾   Swimlanes: None ▾   (P2)                        │
│ ┌─Backlog─┐ ┌─To Do──┐ ┌─In Prog.─┐ ┌─In Review┐ ┌─Done──┐          │
│ │  (18)   │ │  (6)   │ │ (4) WIP:5│ │  (2)     │ │ (11)  │          │
│ ├─────────┤ ├────────┤ ├──────────┤ ├──────────┤ ├───────┤          │
│ │┌───────┐│ │┌──────┐│ │┌────────┐│ │┌────────┐│ │       │          │
│ ││🐞PLS-9 ││ ││◻PLS-3││ ││◻PLS-7  ││ ││◻PLS-5  ││ │       │          │
│ ││Login…  ││ ││Copy… ││ ││API pag ││ ││Nav a11y││ │       │          │
│ ││◆3 🔴 👤││ ││◆2 👤 ││ ││◆5 🟠 👤││ ││◆8 👤👤 ││ │       │          │
│ │└───────┘│ │└──────┘│ │└────────┘│ │└────────┘│ │       │          │
│ │[+ add]  │ │[+ add] │ │[+ add]   │ │          │ │       │          │
│ └─────────┘ └────────┘ └──────────┘ └──────────┘ └───────┘          │
└──────────────────────────────────────────────────────────────────────┘
```

**Key components.**
- **Columns** = Pulse Task Workflow states (§5 canonical). Header shows state name, count, and (P2) WIP limit.
- **Card** shows: type icon, `KEY`, title (2-line clamp), story-point pill (`◆`), priority dot, label chips, assignee avatar(s) from `_assign`, sub-task/checklist progress, comment/attachment count badges.
- **Quick-add** row at column bottom (`+ add`): type title, Enter creates a Task in that state.
- **Board toolbar:** sprint scope selector, Filter, Group-by, Swimlanes (P2), overflow menu (board settings), Create.

**Interactions.**
- **Drag-drop** card between columns → transitions `workflow_state` (respects allowed transitions/roles; a disallowed drop snaps back with a toast). Reorder within a column persists `pulse_rank`.
- **Optimistic**: card moves instantly; server reconciles; status-log row written by doc-event.
- Click card → Rich Task pane (URL-addressable `…/board?task=PLS-7`). Hover → quick actions (assign, points, move).
- **Inline**: click points pill to edit; click avatar to reassign (Autocomplete of eligible users per hierarchy rule §6).
- **WIP limit (P2):** column turns amber when over limit; drop still allowed but flagged.
- **Swimlanes (P2):** group rows by Assignee / Epic / Priority.
- Multi-select (Shift/Ctrl-click) → bulk move/assign (§5.6).

**States.**
- *Empty board:* "No tasks yet. Add your first card." + quick-add focused.
- *Empty column:* muted "Drop cards here" dashed well.
- *Loading:* skeleton columns with 3 shimmer cards each.
- *Error:* column-level retry; a failed drag reverts and toasts "Move failed — you may not have permission."
- *Filtered-empty:* "No cards match these filters. Clear filters."

**Data.** Lean board payload per canonical model: Task `name`, key, title, `workflow_state`, `priority`, `pulse_story_points`, `pulse_rank`, `_assign`, labels (`_user_tags`), sub-task/comment/attachment counts, `pulse_sprint`. Scoped by project + (optional) active sprint.

**Phase.** **P1:** **Frappe Kanban Board** doctype configured with columns = workflow states; native drag, quick-add. **P2:** custom frappe-ui board with WIP/swimlanes/optimistic DnD/virtualization. **P3:** saved board views per user.

---

### 4.3 Backlog

**Purpose.** An ordered, groom-able list of all not-yet-done work; drag to prioritize; pull items into sprints.

**Layout.**
```
┌ Website Revamp · Backlog ───────────────────  [Filter] [⋯] [+ Task]┐
│ ┌ Sprint 4 (Active) · 21 pts ───────────────────────────────────┐ │
│ │ ⠿ ◻ PLS-3  Onboarding copy         ◆2  👤   To Do            │ │
│ │ ⠿ ◻ PLS-7  API pagination          ◆5  👤   In Progress      │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ ┌ Sprint 5 (Planned) · 13 pts ─────────────────  [Start sprint]─┐ │
│ │ ⠿ 📗 PLS-31 Search redesign         ◆8  —                     │ │
│ └───────────────────────────────────────────────────────────────┘ │
│ ┌ Backlog · 64 pts ─────────────────────────────────────────────┐ │
│ │ ⠿ 🐞 PLS-40 Fix 500 on export       ◆3  —                     │ │
│ │ ⠿ 📗 PLS-41 Bulk import             ◆—  —   [estimate]        │ │
│ │ [+ add task]                                                   │ │
│ └───────────────────────────────────────────────────────────────┘ │
│                                       ▸ Sprint Planning panel (P2) │
└──────────────────────────────────────────────────────────────────────┘
```

**Key components.** Collapsible **sections** (Active sprint, Planned sprints, Backlog); each row = compact task line with drag handle (`⠿`), type icon, key, title, inline points, assignee, status. Right-side **Sprint Planning panel** (P2): capacity, committed vs planned points, working-days-adjusted (Holiday List).

**Interactions.**
- **Drag to reorder** within backlog → persists `pulse_rank` (lower = higher). Debounced, optimistic.
- **Drag into a sprint section** → sets `pulse_sprint`. Multi-select drag supported.
- **Inline edit:** title, points, assignee, type — click to edit in place.
- Right-click / `⋯` row menu: Move to sprint ▸, Set points, Assign, Convert to Epic, Delete.
- **Start sprint** from a Planned sprint header → confirm dialog (dates, goal).
- Filter by type/label/assignee/epic; search.

**States.**
- *Empty backlog:* "Your backlog is clear. Add tasks to plan ahead." + add row.
- *Empty sprint section:* "Drag tasks here to plan this sprint."
- *Loading:* shimmer rows grouped by section.
- *Unestimated highlight:* rows with no points show a subtle `[estimate]` affordance.

**Data.** Tasks where `workflow_state != Done/Cancelled`, ordered by `pulse_rank`, grouped by `pulse_sprint` state (Active/Planned/none). Points sums per section. Capacity from Sprint dates + `working_days_source` Holiday List.

**Phase.** **P1:** Desk Task **list view** sorted by `pulse_rank`, with a bulk "Assign Sprint" action; reorder via editing rank. **P2:** true drag-to-reorder backlog + sprint planning panel. **P3:** capacity forecasting from velocity.

---

### 4.4 Sprint Planning & Sprint Execution

Two related views around the **Pulse Sprint** doctype (states: `Planned` → `Active` → `Completed`; one Active per project).

#### 4.4a Sprint Planning

**Purpose.** Compose an upcoming sprint: set goal/dates, pull items from backlog until capacity is met.

**Layout.** Two-pane: left = **Backlog source list**; right = **Sprint draft** (goal field, date range, running point total vs capacity bar). Central `→ Add` / drag moves items.

```
┌ Sprint 5 · Planning ──────────────────────────────────────────────┐
│  BACKLOG (source)            │  SPRINT 5 (draft)                    │
│  🐞 PLS-40 ◆3   [→]          │  Goal: [ Ship new search…        ]   │
│  📗 PLS-41 ◆5   [→]          │  Dates: [Jul 7] – [Jul 20]           │
│  📗 PLS-31 ◆8   [→]          │  Capacity ▓▓▓▓▓▓░░ 13 / 20 pts       │
│                              │  ◻ PLS-31 Search redesign  ◆8 [×]    │
│                              │  ◻ PLS-40 Fix 500 export   ◆3 [×]    │
│                              │  [ Start Sprint ]   [ Save Draft ]   │
└────────────────────────────────────────────────────────────────────┘
```

**Interactions.** Drag/`→` add & remove; capacity bar turns amber over capacity; edit goal/dates inline; **Start Sprint** validates (dates set, ≥1 task, no other Active sprint) then transitions to Active and stamps `is_active`.

**States.** Empty draft: "Add tasks from the backlog to plan this sprint." Over-capacity warning (non-blocking). Error if a second Active sprint attempted → "This project already has an active sprint."

**Data.** Pulse Sprint (`planned_points` computed live), backlog Tasks, Holiday List for working days.

#### 4.4b Sprint Execution

**Purpose.** Run the active sprint day-to-day: board scoped to sprint + burndown at a glance.

**Layout.** Header strip: sprint name, goal, days remaining, points remaining, mini-burndown sparkline, `[Complete Sprint]`. Body = the Board (§4.2) filtered to the active sprint. Side widget: **Burndown** chart.

**Interactions.** Same board interactions, scoped to sprint. **Complete Sprint** → summary dialog (completed vs planned points, spillover list with "move to next sprint / backlog" choices) → sets sprint `Completed`, computes `velocity`, moves unfinished tasks per user choice.

**States.** No active sprint → "No active sprint. Plan one from the Backlog." Sprint ended (past end date, still Active) → amber "Sprint overdue — complete it?" banner.

**Data.** Pulse Sprint + its Tasks + Status Log (for burndown) + Timesheet (for actual-hours widget).

**Phase.** **P1:** Sprint = Desk form; execution = Kanban Board filtered by `pulse_sprint`; burndown = Dashboard Chart. **P2:** dedicated planning/execution SPA screens with drag + live capacity + in-line burndown. **P3:** cross-sprint carryover analytics.

---

### 4.5 Rich Task Detail (pane / modal)

**Purpose.** One pane to see and edit everything about a Task — the Plane/Jira "issue view."

**Layout.** Right-side drawer (desktop) or full-screen modal (mobile). Two columns: **main** (description, sub-tasks, checklist, activity) + **sidebar** (properties).

```
┌ PLS-7 · API pagination ─────────────────────────────── [↗ open] [×]┐
│ MAIN                                   │ PROPERTIES                  │
│ [In Progress ▾]  📗 Story             │ Assignees  👤 Priya  [+]    │
│ Title (inline editable)               │ Reporter   👤 Sam           │
│                                       │ Status     In Progress      │
│ Description (rich text) …             │ Priority   🟠 High          │
│                                       │ Story Pts  ◆ 5              │
│ ▸ Sub-tasks (2/3)                     │ Sprint     Sprint 4         │
│   ☑ PLS-7a  Cursor param              │ Epic       ◫ Search         │
│   ☐ PLS-7b  Docs                      │ Labels     [backend][api]   │
│ ▸ Checklist (3/5)  ▰▰▰▱▱             │ Due        Jul 12           │
│ ▸ Dependencies:  blocks PLS-9         │ Est/Actual 8h / 5.5h ⓘTS    │
│ ── Tabs: Activity | Comments | Files | Time Log ──                  │
│  💬 comment box …                      │                             │
└──────────────────────────────────────────────────────────────────────┘
```

**Key components & data source.**
- **Status** dropdown = workflow transition (role-gated); writes status-log.
- **Title / Description** — inline + rich text (Frappe editor).
- **Sub-tasks** = child Tasks via `parent_task` (add inline; each is a real Task).
- **Checklist** = simple checklist child on Task (extend only if truly needed — canonical §18 prefers sub-tasks).
- **Dependencies** = Task `depends_on` (blocks/blocked-by).
- **Comments** = Frappe Comment/Communication; **Activity** = Version/timeline; **Files** = File attachments; all reused.
- **Time Log** tab = **Timesheet Detail** rows for this task; **Actual** hours are the sum (never hand-entered); "Log time" opens a Timesheet entry.
- **Sidebar properties:** Assignees (`_assign`, hierarchy-limited picker), Priority, `pulse_story_points`, `pulse_sprint`, `pulse_epic`, labels (`_user_tags`), due date, Est vs Actual.

**Interactions.** Everything inline-editable & optimistic. `↗` opens the Task in Desk form (finance/ops). Keyboard: `E` edit title, `A` assign, `S` status, `M` move sprint, `Esc` close. Deep-linkable (`?task=PLS-7`).

**States.** Loading skeleton pane; not-found → "Task not found or no access"; permission-limited → read-only badges, disabled editors; conflict (modified elsewhere) → "This task changed — reload."

**Phase.** **P1:** standard ERPNext **Task form** (all fields present via custom fields; sub-tasks, comments, timeline, attachments, timesheet links are native). **P2:** frappe-ui rich pane over the same Task. **P3:** links/relations polish, pages/docs embed.

---

### 4.6 Roadmap / Timeline & Epics (Phase 3 / Phase 2)

#### 4.6a Roadmap / Timeline (Phase 3)

**Purpose.** Portfolio-level, time-based plan of epics/sprints/releases.

**Layout.** Gantt-style timeline: rows = Epics (or Sprints/Releases), horizontal bars across a month/quarter axis; dependency arrows; "today" line; zoom (week/month/quarter).

```
┌ Roadmap ─────────────────────  [Week|Month|Quarter]  [Filter]──────┐
│                Jul        Aug        Sep                            │
│ ◫ Search      ▓▓▓▓▓▓▓▓░░                                            │
│ ◫ Payments             ▓▓▓▓▓▓▓▓▓▓░░                                 │
│ ◫ Mobile                        ▓▓▓▓▓▓▓▓▓▓                          │
│  ↳ dependency PLS-9 → PLS-31 (arrow)                                │
└──────────────────────────────────────────────────────────────────────┘
```

**Interactions.** Drag bar ends to reschedule (updates Task/Epic `exp_start_date`/`exp_end_date`); click bar → Epic detail; collapse epic to show child stories. Lazy-load date ranges; virtualize rows.

**States.** Empty: "No epics or dated work to show yet." Loading: shimmer rows.

**Data.** Epics (Task Type=Epic) + child Tasks' `exp_start_date`/`exp_end_date`, Sprints, `pulse_release`.

**Phase.** **P1:** reuse Frappe **Gantt view** on Task (read-mostly). **P3:** interactive SPA roadmap.

#### 4.6b Epics view (Phase 2)

**Purpose.** List of Epics with rolled-up progress.

**Layout.** List/cards: each Epic shows title, point progress bar (done/total from child stories), child count, status, target release.

**Interactions.** Expand to see child stories; click → Epic Rich Task pane; create story under epic; filter by release/status.

**Data.** Task Type=Epic + children via `parent_task`/`pulse_epic`; points rolled up from children.

---

### 4.7 Reports / Analytics

**Purpose.** Delivery-oriented metrics (Doc 0 §7 gap). All built on the **Frappe reporting engine** (Dashboard Chart / Number Card / Query & Script Report) — never a bespoke chart engine.

**Layout.** Reports hub with a grid of chart cards + a filter bar (project, sprint, date range). Each chart expands to a full report.

```
┌ Reports · Website Revamp ───────  [Sprint ▾] [Range ▾] [Export]────┐
│ ┌ Velocity ────────┐ ┌ Burndown (Sprint 4) ┐ ┌ Cycle time ──────┐ │
│ │ ▂▄▆█▅  avg 18pts │ │  ╲ ideal            │ │  median 3.2d      │ │
│ │  S1 S2 S3 S4 S5  │ │   ╲__ actual        │ │  ▁▂▅▃▂            │ │
│ └──────────────────┘ └─────────────────────┘ └──────────────────┘ │
│ ┌ Burnup ──────────┐ ┌ Cumulative Flow ────┐ ┌ Workload ────────┐ │
│ │  scope vs done   │ │  stacked states/day │ │  pts per assignee │ │
│ └──────────────────┘ └─────────────────────┘ └──────────────────┘ │
│ ── Sprint Report: planned vs completed, added/removed, spillover ──│
└──────────────────────────────────────────────────────────────────────┘
```

**Reports (per canonical §8).** Velocity, Burndown, Burnup, Cumulative Flow Diagram, Cycle/Lead Time, Workload, Sprint Report. Actual-hours metrics derive from **Timesheet**.

**Interactions.** Change scope/filter; hover tooltips; drill from a chart to the underlying task list; export CSV/PDF (reuse Frappe export).

**States.** Not-enough-data (e.g., <2 sprints for velocity) → "Complete a sprint to see velocity." Loading skeleton charts. Error per-card retry.

**Data.** Pulse Task Status Log (burndown/burnup/CFD/cycle time), Pulse Sprint (velocity/sprint report), `_assign`+points (workload), Timesheet (actuals).

**Phase.** **P1:** Dashboard Charts + Number Cards + Script/Query reports in Desk/workspace (Velocity + Burndown for MVP). **P2:** Burnup, CFD, Cycle/Lead time; SPA reports hub. **P3:** portfolio analytics & forecasting.

---

### 4.8 Project Settings & Pulse Settings

#### 4.8a Project Settings

**Purpose.** Per-project agile configuration (opt-in Scrum, board type, sprint defaults, key).

**Layout.** Tabbed settings page: **General** (name, customer, dates — reused Project fields), **Agile** (`pulse_enable_scrum`, `pulse_board_type` Scrum/Kanban, `pulse_default_sprint_length`, `pulse_project_key`), **Board** (column/WIP config — P2), **Members & Access** (Project Users / roles), **Workflow** (which Pulse Task Workflow).

**Interactions.** Toggle Enable Scrum → shows/hides Backlog & Sprints nav (P2). Set project key → drives card refs. Save via standard document API (permissions apply).

**States.** Non-admin → read-only. Unsaved-changes guard.

**Data.** Project + Pulse custom fields (§4 canonical). Members = Project User child + Has Role.

#### 4.8b Pulse Settings (app-level)

**Purpose.** Global defaults & policy. Backed by the **Pulse Settings** Single doctype.

**Layout.** Sections: **Defaults** (`default_sprint_length_days`, `default_board_type`), **Assignment** (`enable_hierarchical_assignment` + **Role Ranks** table → Pulse Role Rank), **Notifications** (`email_notifications`, `desktop_notifications`), **Calendar** (`working_days_source` Holiday List).

```
┌ Pulse Settings ────────────────────────────────────────────────────┐
│ Defaults                                                            │
│   Sprint length (days) [ 14 ]   Board type [ Scrum ▾ ]             │
│ Assignment                                                          │
│   [✓] Hierarchical assignment                                      │
│   Role ranks:  Pulse Admin 100 · Manager 80 · Team Lead 60 …  [+]  │
│ Notifications  [✓] Email  [✓] Desktop                              │
│ Calendar  Working days from [ Holiday List ▾ ]                     │
└──────────────────────────────────────────────────────────────────────┘
```

**Interactions.** Edit role-rank rows (drives §6 hierarchy). Toggles. Save.

**States.** Requires `Pulse Admin`; others read-only or hidden.

**Data.** Pulse Settings Single + Pulse Role Rank child; Role & Holiday List links.

**Phase.** **P1:** Desk Single form + Project form (custom fields). **P2:** styled SPA settings screens over the same doctypes.

---

## 5. Interaction Patterns

### 5.1 Drag-and-drop
- **Board:** drag card between columns (transition `workflow_state`) and within a column (reorder → `pulse_rank`).
- **Backlog:** drag to reorder (`pulse_rank`) and into sprint sections (`pulse_sprint`).
- **Roadmap:** drag bar to reschedule dates (P3).
- All DnD: 8px drag threshold, ghost preview, drop-target highlight, ARIA live-region announcements ("PLS-7 moved to In Progress"), snap-back on rejected drop. Persistence debounced (250ms) and optimistic.

### 5.2 Inline edit
- Click a field (title, points, assignee, priority, due) to edit in place; Enter/blur saves, Esc cancels. No modal for single-field edits. Optimistic with rollback.

### 5.3 Optimistic updates
- Mutations render immediately from local state; a background write reconciles. On server rejection (permission, validation, workflow), the UI reverts and shows a `toast` with the reason. Status-log rows are server-written by doc-event, so metrics stay authoritative.

### 5.4 Quick-add
- Board column and list footers show `+ add`; type a title, Enter creates a Task in that column/section with sensible defaults (project, state, sprint, rank). `Shift+Enter` keeps the composer open for rapid entry.

### 5.5 Keyboard shortcuts

| Key | Action |
|---|---|
| `⌘/Ctrl+K` | Command palette |
| `C` | Create task |
| `/` | Focus search/filter |
| `G` then `B`/`L`/`S`/`R` | Go to Board / Backlog / Sprints / Reports |
| `J` / `K` | Next / previous card (focus) |
| `Enter` | Open focused card |
| `E` | Edit title (in pane) |
| `A` | Assign |
| `S` | Change status |
| `M` | Move to sprint |
| `X` | Toggle select (multi) |
| `Esc` | Close pane / cancel edit |
| `?` | Shortcut cheatsheet |

### 5.6 Bulk actions
- Multi-select cards/rows (Shift-range, Ctrl-toggle, or `X`). A floating action bar appears: **Assign · Set status · Move to sprint · Set points · Add label · Delete**. Each applies through the standard document API so permissions/validation fire per item; partial failures are reported per-row.

### 5.7 Filters & saved views
- Filter bar per screen: project, type, status, assignee, label, priority, epic, sprint, due. Filters are URL-encoded (shareable/deep-linkable). **Saved views** (P2+): name a filter+group+sort combination; pin to left nav. Reuses Frappe's filter semantics on the server.

---

## 6. Empty / Loading / Error State Guidance

**Principles.** Every list/board/chart defines all four states. Empty states teach and offer the next action; loading uses skeletons matching final layout; errors are recoverable and specific.

- **Empty (first-run):** illustration + one-line explanation + single primary CTA. E.g., Board: "No tasks yet — add your first card" with quick-add focused. Backlog: "Your backlog is clear." Reports/velocity: "Complete a sprint to see velocity."
- **Empty (filtered):** "No items match these filters." + **Clear filters** button (distinct from first-run empty).
- **Loading:** skeleton shells (columns/rows/cards/charts) — never a bare spinner on primary content. First meaningful paint < 1s.
- **Error:** scoped to the smallest unit (column, card, chart) with a **Retry**; global errors as a dismissible banner. Messages name the cause where known ("You may not have permission to move this card", "This project already has an active sprint"). Optimistic-write failures always roll back and toast.
- **Permission-limited (not an error):** show data read-only with disabled affordances rather than hiding it entirely, unless the user lacks read access (then it simply doesn't appear).
- **Offline/conflict:** "You're offline — changes will retry"; "This task changed elsewhere — reload."

---

## 7. Responsive, Mobile & Accessibility

### 7.1 Responsive breakpoints
- **≥1280px (desktop):** full left nav + multi-column board + right-drawer task pane.
- **768–1279px (tablet):** collapsible left nav (icon rail); board scrolls horizontally; task pane = drawer over content.
- **<768px (mobile):** bottom tab bar (My Work · Board · Backlog · Create · More); board becomes **single-column, swipe between statuses**; task detail = full-screen modal; backlog = single list with swipe actions.

### 7.2 Mobile behavior
- Touch-first: long-press to pick up a card, drag to reorder; swipe-left on a row for quick actions (assign/status). Larger 44px tap targets. Quick-add via a floating `+`.
- Roadmap/Gantt is view-only on mobile (pan/zoom, no bar-drag).
- Phase 3 delivers a mobile-optimized/PWA pass (Doc 0 §33).

### 7.3 Accessibility (WCAG 2.1 AA)
- **Keyboard:** full operability (§4.2, §5.5); visible focus rings (`--pulse-focus-ring`); logical tab order; board cards focusable with arrow-key navigation and keyboard move (`Space` grab, arrows move, `Enter` drop).
- **ARIA:** board columns `role="list"`, cards `role="listitem"` with `aria-roledescription="draggable card"`; DnD announced via `aria-live="polite"` region; dialogs/drawers use `role="dialog"` + focus trap + `Esc`; icon-only buttons have `aria-label`.
- **Color & contrast:** status/priority/type never conveyed by color alone (icon + text always present); text ≥ 4.5:1, UI/non-text ≥ 3:1; verified in both light and dark themes.
- **Motion:** honor `prefers-reduced-motion` (disable non-essential transitions/DnD animation).
- **Forms:** every control labeled; inline validation announced; error summaries linked to fields.
- **Screen readers:** card announces "PLS-7, Story, API pagination, In Progress, 5 points, assigned to Priya."

---

## 8. Phase 1 (Desk / Kanban reuse) ↔ Phase 2 (SPA) Mapping

Reuse-first: **ship working software in Phase 1 with almost no custom UI**, then elevate the experience in Phase 2. Same data, same permissions, two front-ends.

| Screen | **Phase 1 — Desk/Kanban reuse** | **Phase 2 — frappe-ui SPA** | **Phase 3** |
|---|---|---|---|
| Nav / IA | Desk **Pulse workspace** with shortcuts | SPA left-nav + Command-K at `/pulse` | Saved views, portfolio switcher |
| Dashboard / My Work | ERPNext "Assigned to me" list + Number Cards | SPA My Work (personal board, mentions) | — |
| Board (Kanban) | **Frappe Kanban Board** (columns = workflow states, native DnD, quick-add) | Custom board: WIP limits, swimlanes, optimistic DnD, virtualization | Saved board views |
| Backlog | Task **list view** sorted by `pulse_rank` + bulk "assign sprint" | Drag-to-reorder backlog + sprint planning panel | Capacity forecasting |
| Sprint plan/exec | Pulse Sprint **Desk form** + Kanban filtered by sprint; burndown = Dashboard Chart | Dedicated planning/execution screens, live capacity, inline burndown | Carryover analytics |
| Rich Task detail | ERPNext **Task form** (all fields via custom fields; native subtasks/comments/timeline/files/timesheet) | frappe-ui rich pane (drawer/modal) over same Task | Relations, pages/docs embed |
| Roadmap / Timeline | Frappe **Gantt view** on Task (read-mostly) | (Epics view) | Interactive SPA roadmap |
| Epics | Task list filtered Type=Epic | Epics view with rolled-up progress | Roadmap integration |
| Reports | Dashboard Charts + Number Cards + Script/Query reports (Velocity, Burndown) | SPA reports hub + Burnup/CFD/Cycle-Lead | Portfolio analytics/forecast |
| Project Settings | Project **Desk form** (Pulse custom fields) | Styled SPA settings tabs | — |
| Pulse Settings | Pulse Settings **Single** Desk form + Role Ranks child | Styled SPA settings | — |

**Design implication.** Phase 1 UX is deliberately constrained by what Desk/Kanban already do well — the win is *working, financially-integrated agile*, not polish. Phase 2 is where Pulse earns "as modern as Plane/Jira": the SPA reimplements Board, Backlog, Sprint, and the Rich Task pane over the identical core Task/Project/Sprint data, with optimistic UI, DnD, Command-K, and the design tokens in §2. No screen ever forks the data model to gain UX — the card is always an ERPNext Task.

---

*End of Document 8 — UI/UX Specification. Next: Document 9 (per the documentation set).*
