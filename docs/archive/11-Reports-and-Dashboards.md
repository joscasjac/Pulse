# Pulse — Reports and Dashboards

**Document 11 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. Reporting Strategy — Reuse the Frappe Reporting Engine

Pulse ships **zero** custom charting code, **zero** bespoke aggregation services, and **no** parallel analytics store. Every metric is delivered through the reporting primitives that Frappe/ERPNext already provide and that every ERPNext admin already knows how to configure:

| Primitive | Role in Pulse | Why reuse |
|---|---|---|
| **Query Report** | Simple, single-SQL metrics (Velocity, Workload) | Fastest, declarative, permission-aware via role restrictions |
| **Script Report** | Metrics needing per-day iteration / working-day math (Burndown, Burnup, CFD, Cycle/Lead Time, Sprint Report) | Python controller can walk Status Log rows and sprint dates |
| **Dashboard Chart** | Visual rendering of a report or a doctype aggregate | Native chart types, cached, embeddable on any workspace |
| **Number Card** | Single-figure KPIs (active sprint points, spillover, avg cycle time) | Native, cached, permission-aware |
| **Report Builder / List View** | Ad-hoc slicing (backlog, my tasks) | Free, no code |
| **Workspace** | Persona dashboards assembling the above | Native layout, role-visibility |

**Hard rules for this document**

1. **Metrics read only from three sources:** `Pulse Task Status Log` (timestamped transitions), `Task` (story points, sprint, status, dates), and `Timesheet` / `Timesheet Detail` (actual hours). Story-point math for time-series metrics uses `points_at_change` snapshotted on the Status Log — never the live Task value, so historical charts stay correct after re-estimation.
2. **Actuals come from Timesheet, never hand-entered.** Any "actual effort / hours" figure aggregates `Timesheet Detail.hours`. Story points are estimation only; they are never actuals.
3. **Permissions are enforced by the engine.** Reports declare `roles`; Script Report queries pass `user`/apply standard permission filters. **No report or chart blanket-bypasses permissions.** A Developer sees only projects they can access.
4. **No status field for agile state.** Board/agile state is `workflow_state` (Frappe Workflow, canonical model §5), recorded historically in the Status Log. Reports read `to_state` from the log, not a custom status column.

---

## 2. Per-Report Specifications

Naming convention for all report doctypes: `Pulse <Metric>` in module **Pulse**. All are shipped as fixtures.

Common filters (offered by most reports): `project` (Link → Project), `sprint` (Link → Pulse Sprint), `from_date` / `to_date`, `assignee` (Link → User), `task_type` (Link → Task Type). Filters are applied as SQL `WHERE` clauses / Script Report `filters` so the engine handles them.

---

### 2.1 Velocity

- **Report type:** Query Report — `Pulse Velocity`
- **Purpose:** How many story points a team completes per sprint; the basis for forecasting future sprint capacity.
- **Data source:** `Pulse Sprint` (`completed_points`, `planned_points`, `status`, `end_date`, `project`) — these are computed read-only fields set at sprint close. Cross-check against `Pulse Task Status Log` where `to_state = 'Done'` and `sprint = <sprint>` (sum of `points_at_change`) is available for the drill-down variant.
- **Filters:** `project` (reqd), `last_n_sprints` (Int, default 6).
- **Columns:** Sprint | Start Date | End Date | Planned Points | Completed Points | Velocity (= completed) | Attainment % (completed/planned).
- **Calculation (words):** For each completed sprint in the project, take the points that reached `Done` before sprint end. Velocity = completed points. Attainment = completed ÷ planned.
- **Pseudo-SQL:**
  ```sql
  SELECT s.name AS sprint, s.start_date, s.end_date,
         s.planned_points, s.completed_points,
         s.completed_points AS velocity,
         ROUND(100 * s.completed_points / NULLIF(s.planned_points,0), 1) AS attainment_pct
  FROM `tabPulse Sprint` s
  WHERE s.project = %(project)s AND s.status = 'Completed'
  ORDER BY s.end_date DESC
  LIMIT %(last_n_sprints)s;
  ```
- **Chart type:** Bar (completed points per sprint) + a dashed average line; overlay planned as a faint bar for attainment.
- **Phase:** Phase 1 (MVP).

---

### 2.2 Burndown

- **Report type:** Script Report — `Pulse Burndown`
- **Purpose:** Remaining work (story points) in the active sprint plotted against an ideal straight-line burn to zero by sprint end. Answers "are we on track to finish the sprint?"
- **Data source:** `Pulse Task Status Log` (`to_state`, `changed_on`, `points_at_change`, `sprint`), `Pulse Sprint` (`start_date`, `end_date`, `planned_points`), and `working_days_source` (Holiday List from Pulse Settings / Project) to build the ideal line over working days only.
- **Filters:** `sprint` (reqd; defaults to active sprint for the chosen project), `project`.
- **Columns (tabular form):** Date | Ideal Remaining | Actual Remaining | Points Completed That Day | Points Added That Day.
- **Calculation (words):** Start with the sprint's committed points (planned_points at start). For each calendar day from `start_date` to `end_date`: subtract points whose Status Log transition to `Done` occurred on/before that day; add points for tasks added to the sprint after start (scope change). The **ideal line** decreases linearly by `committed_points ÷ number_of_working_days`, stepping down only on working days (per Holiday List). Remaining never derived from the live Task point value — always `points_at_change`.
- **Pseudo-SQL (core per-day query, run inside the Script Report loop):**
  ```sql
  -- committed at sprint start
  SELECT COALESCE(SUM(points_at_change),0) AS committed
  FROM `tabPulse Task Status Log`
  WHERE sprint = %(sprint)s AND changed_on <= %(start_date)s;

  -- cumulative completed up to :day
  SELECT COALESCE(SUM(points_at_change),0) AS done
  FROM `tabPulse Task Status Log` l
  WHERE l.sprint = %(sprint)s AND l.to_state = 'Done'
    AND l.changed_on <= %(day_end)s
    AND l.name = (  -- latest transition per task on/before day
        SELECT l2.name FROM `tabPulse Task Status Log` l2
        WHERE l2.task = l.task AND l2.changed_on <= %(day_end)s
        ORDER BY l2.changed_on DESC LIMIT 1);
  -- actual_remaining[day] = committed + added_up_to_day - done
  ```
- **Chart type:** Line — two series (Ideal dashed, Actual solid), X = date, Y = remaining points.
- **Snapshotting:** See §7 — daily scheduled snapshot recommended for large sprints; computed on-the-fly for the current day.
- **Phase:** Phase 1 (MVP).

---

### 2.3 Burnup

- **Report type:** Script Report — `Pulse Burnup`
- **Purpose:** Two lines — total scope and completed work — over time. Unlike burndown, burnup makes **scope change visible** (the scope line moves).
- **Data source:** `Pulse Task Status Log` (`points_at_change`, `to_state`, `changed_on`, `sprint`) for the completed line; sum of in-sprint task points over time (scope line) derived from log rows where a task's latest membership shows `sprint = <sprint>`.
- **Filters:** `sprint` (reqd), `project`.
- **Columns:** Date | Scope (total points) | Completed points.
- **Calculation (words):** For each day: **Scope** = sum of `points_at_change` for all tasks that are members of the sprint as of that day; **Completed** = cumulative points that reached `Done` on/before that day. Sprint is finished when Completed meets Scope.
- **Pseudo-SQL (per-day):**
  ```sql
  -- scope as of day
  SELECT COALESCE(SUM(points_at_change),0) FROM (
    SELECT DISTINCT task, points_at_change
    FROM `tabPulse Task Status Log`
    WHERE sprint = %(sprint)s AND changed_on <= %(day_end)s
  ) t;
  -- completed as of day: same 'done' subquery as burndown
  ```
- **Chart type:** Line — Scope (upper) and Completed (rising to meet it); shaded gap = remaining.
- **Phase:** Phase 2.

---

### 2.4 Cumulative Flow Diagram (CFD)

- **Report type:** Script Report — `Pulse Cumulative Flow`
- **Purpose:** Stacked count of tasks in each workflow state per day. Band widths reveal bottlenecks (a widening "In Progress" band = WIP piling up) and lead-time trends.
- **Data source:** `Pulse Task Status Log` only — `to_state`, `changed_on`, plus `project`/`sprint` for filtering. State list from the Pulse Task Workflow (`Backlog`, `To Do`, `In Progress`, `In Review`, `Done`; `Cancelled` excluded from the stack).
- **Filters:** `project` (reqd), `sprint` (optional), `from_date`, `to_date`.
- **Columns:** Date | Backlog | To Do | In Progress | In Review | Done.
- **Calculation (words):** For each day and each state, count tasks whose **latest** transition on/before that day landed in that state. Rows summed = total live tasks (excluding Cancelled). This is a count-of-tasks CFD (a points variant can sum `points_at_change`).
- **Pseudo-SQL (per day; latest state per task):**
  ```sql
  SELECT cur.to_state, COUNT(*) AS cnt
  FROM (
    SELECT l.task, l.to_state
    FROM `tabPulse Task Status Log` l
    JOIN (
      SELECT task, MAX(changed_on) AS mx
      FROM `tabPulse Task Status Log`
      WHERE changed_on <= %(day_end)s AND project = %(project)s
      GROUP BY task
    ) m ON m.task = l.task AND m.mx = l.changed_on
  ) cur
  WHERE cur.to_state != 'Cancelled'
  GROUP BY cur.to_state;
  ```
- **Chart type:** Stacked area, X = date, Y = task count, one band per state.
- **Phase:** Phase 2.

---

### 2.5 Cycle Time

- **Report type:** Script Report — `Pulse Cycle Time`
- **Purpose:** Elapsed working time from when a task **starts** (first enters `In Progress`) to when it reaches `Done`. Measures execution efficiency.
- **Data source:** `Pulse Task Status Log` — per task, the earliest `changed_on` where `to_state = 'In Progress'` and the `changed_on` where `to_state = 'Done'`.
- **Filters:** `project` (reqd), `sprint`, `from_date`/`to_date` (on Done date), `task_type`, `assignee`.
- **Columns:** Task | Type | Started On | Done On | Cycle Time (days) | Cycle Time (working days).
- **Calculation (words):** Cycle time = Done timestamp − first In-Progress timestamp. Provide both calendar days and working days (subtract Holiday-List non-working days). Report footer/summary emits average, median, and 85th percentile for the KPI number cards.
- **Pseudo-SQL:**
  ```sql
  SELECT ip.task,
         ip.started_on,
         dn.done_on,
         TIMESTAMPDIFF(HOUR, ip.started_on, dn.done_on)/24.0 AS cycle_days
  FROM (
     SELECT task, MIN(changed_on) AS started_on
     FROM `tabPulse Task Status Log`
     WHERE to_state = 'In Progress' AND project = %(project)s
     GROUP BY task) ip
  JOIN (
     SELECT task, MIN(changed_on) AS done_on
     FROM `tabPulse Task Status Log`
     WHERE to_state = 'Done' AND project = %(project)s
     GROUP BY task) dn ON dn.task = ip.task
  WHERE dn.done_on BETWEEN %(from_date)s AND %(to_date)s;
  ```
- **Chart type:** Scatter (Done date vs cycle days) or histogram of cycle-time buckets; control-chart style.
- **Phase:** Phase 2.

---

### 2.6 Lead Time

- **Report type:** Script Report — `Pulse Lead Time`
- **Purpose:** Elapsed time from task **creation/entry into the backlog** to `Done`. Includes wait time before work started — the customer-facing "how long from ask to delivery".
- **Data source:** `Pulse Task Status Log` — first ever transition (or `Task.creation`) as the start anchor, and first `to_state = 'Done'` as the end.
- **Filters:** same as Cycle Time.
- **Columns:** Task | Type | Created / Backlog On | Done On | Lead Time (days) | Lead Time (working days).
- **Calculation (words):** Lead time = Done timestamp − earliest Status Log `changed_on` for the task (fallback `Task.creation` if no earlier log). Working-day variant subtracts Holiday-List days. Summary emits avg/median/p85. **Difference from cycle time:** lead time counts the queue/backlog wait; cycle time starts only at first In-Progress.
- **Pseudo-SQL:**
  ```sql
  SELECT t.name AS task,
         COALESCE(f.first_on, t.creation) AS entered_on,
         dn.done_on,
         TIMESTAMPDIFF(HOUR, COALESCE(f.first_on, t.creation), dn.done_on)/24.0 AS lead_days
  FROM `tabTask` t
  JOIN (SELECT task, MIN(changed_on) done_on
        FROM `tabPulse Task Status Log`
        WHERE to_state='Done' GROUP BY task) dn ON dn.task = t.name
  LEFT JOIN (SELECT task, MIN(changed_on) first_on
        FROM `tabPulse Task Status Log` GROUP BY task) f ON f.task = t.name
  WHERE t.project = %(project)s
    AND dn.done_on BETWEEN %(from_date)s AND %(to_date)s;
  ```
- **Chart type:** Scatter / histogram, same style as cycle time (often plotted together).
- **Phase:** Phase 2.

---

### 2.7 Workload

- **Report type:** Query Report — `Pulse Workload`
- **Purpose:** Open story points (and open task count) per assignee, to spot over/under-allocation during sprint planning and mid-sprint rebalancing.
- **Data source:** `Task` — `_assign` (Frappe assignment field, JSON array), `pulse_story_points`, `pulse_sprint`, `status`/`workflow_state`. Optionally join `Timesheet` for logged-hours context (actuals).
- **Filters:** `project` (reqd), `sprint` (optional; default active), include/exclude Done.
- **Columns:** Assignee | Open Tasks | Open Story Points | Logged Hours (from Timesheet) | Avg Points/Task.
- **Calculation (words):** For each assignee found in `_assign`, sum `pulse_story_points` of tasks not in `Done`/`Cancelled` within scope. Logged Hours = sum of that assignee's `Timesheet Detail.hours` linked to those tasks (actuals from Timesheet only). `_assign` is JSON, so it is unnested in the Script/Query controller (or matched with `LIKE`), never parsed on the client.
- **Pseudo-SQL (simplified; expansion of `_assign` done in the report controller):**
  ```sql
  SELECT assignee,
         COUNT(*)                       AS open_tasks,
         SUM(pulse_story_points)         AS open_points
  FROM `tabTask`
  WHERE project = %(project)s
    AND (%(sprint)s IS NULL OR pulse_sprint = %(sprint)s)
    AND workflow_state NOT IN ('Done','Cancelled')
    AND JSON_CONTAINS(_assign, JSON_QUOTE(assignee))  -- per-assignee in controller loop
  GROUP BY assignee;
  ```
- **Chart type:** Horizontal bar per assignee (open points); optional stacked by state.
- **Phase:** Phase 1 (basic) → Phase 2 (with capacity vs Holiday List).

---

### 2.8 Sprint Report

- **Report type:** Script Report — `Pulse Sprint Report`
- **Purpose:** The sprint-review artifact: what was planned vs completed, what was added/removed mid-sprint (scope change), and what spilled over to the next sprint.
- **Data source:** `Pulse Sprint` (dates, planned/completed points), `Pulse Task Status Log` (membership changes via `sprint` on each row, `to_state`, `points_at_change`), `Task` (current sprint, points, status).
- **Filters:** `sprint` (reqd).
- **Columns / sections:**
  - Summary: Planned Points | Completed Points | Completed % | Added Points | Removed Points | Spillover Points | Spillover Task Count.
  - Detail table: Task | Type | Points | Entered Sprint On | Final State | Outcome (Completed / Spillover / Removed).
- **Calculation (words):**
  - **Committed/Planned** = points in the sprint at `start_date`.
  - **Completed** = points reaching `Done` before `end_date` (from log, `points_at_change`).
  - **Added** = points for tasks joining the sprint after `start_date`; **Removed** = points for tasks leaving before `end_date`.
  - **Spillover** = in-sprint tasks not `Done` at `end_date` (these carry to the next sprint).
- **Pseudo-SQL (spillover example):**
  ```sql
  SELECT t.name, t.pulse_story_points, t.workflow_state
  FROM `tabTask` t
  WHERE t.pulse_sprint = %(sprint)s
    AND t.workflow_state NOT IN ('Done','Cancelled');
  ```
- **Chart type:** Report table + a small planned/completed/added/removed grouped bar; drives the sprint number cards.
- **Phase:** Phase 1 (summary) → Phase 2 (full added/removed/spillover analytics).

---

## 3. Reused ERPNext Reports (as-is)

Because a Pulse card **is** an ERPNext Task and hours **are** ERPNext Timesheets, the standard ERPNext project reports work on Pulse data with no changes. Pulse surfaces them (links/shortcuts on the appropriate persona dashboards) rather than rebuilding them.

| ERPNext report | How it serves Pulse |
|---|---|
| **Project Summary** | Per-project rollup — % complete, task counts, cost/billing. Gives PMs and Execs the financial + delivery snapshot Pulse deliberately does **not** duplicate. Linked from PM/Exec dashboards. |
| **Delayed Tasks Summary** | Lists tasks past `exp_end_date`. Pulse reuses it as the "overdue" view — overdue is a *derived indicator*, never a forced status write (avoids the Appendix-A A4 defect). Surfaced on PM and Team Lead dashboards. |
| **Timesheet Billing Summary** | Billable vs non-billable hours and amounts from Timesheet — the actuals/margin view. Confirms Pulse execution feeds real billing. Exec/PM dashboards. |
| **Daily Timesheet Summary** | Per-user hours logged per day — the actuals feed behind Workload and the developer's own logged-hours view. Developer/Team Lead dashboards. |

These reuse the same Timesheet actuals that Pulse metrics use, guaranteeing one consistent source of truth for hours.

---

## 4. Dashboards per Persona

Dashboards are **Frappe Workspaces** (role-visible), each assembling Number Cards, Dashboard Charts, and report shortcuts. All respect the viewer's permissions — a persona sees only accessible projects.

### 4.1 Project Manager (role: `Pulse Manager`)
- **Number Cards:** Active Sprint Remaining Points · Sprint Completed % · Spillover Task Count · Overdue Tasks · Open Tasks.
- **Charts:** Burndown (active sprint) · Velocity (last 6 sprints) · Cumulative Flow · Workload by assignee.
- **Report shortcuts:** Sprint Report · Project Summary · Delayed Tasks Summary.

### 4.2 Team Lead (role: `Pulse Team Lead`)
- **Number Cards:** My Team Open Points · In-Review Count (bottleneck watch) · Overdue Tasks · Avg Cycle Time.
- **Charts:** Cumulative Flow (WIP health) · Workload by assignee · Burndown (active sprint) · Cycle Time.
- **Report shortcuts:** Workload · Delayed Tasks Summary · Daily Timesheet Summary.

### 4.3 Developer (roles: `Pulse Senior/Junior Developer`, `Pulse Intern`)
- **Number Cards:** My Open Tasks · My Open Points · My Hours Logged (This Week, from Timesheet) · My Overdue Tasks.
- **Charts:** My tasks by state (personal CFD slice) · Sprint Burndown (context).
- **Report shortcuts / list views:** My Tasks (filtered list) · Daily Timesheet Summary (self).
- All personal cards use standard permission filtering — no cross-project disclosure (fixes Appendix-A A5).

### 4.4 Executive (role: `Pulse Admin` / `Projects Manager`)
- **Number Cards:** Portfolio Active Sprints · Avg Velocity (portfolio) · Billable Hours (month) · Portfolio Overdue.
- **Charts:** Velocity trend across projects · Billing (from Timesheet Billing Summary) · Portfolio burnup/health.
- **Report shortcuts:** Project Summary · Timesheet Billing Summary.

---

## 5. Number Cards (master list)

All shipped as fixtures; each declares roles and a permission-aware document-type filter. Cached by the Number Card engine.

| Number Card | Source | Aggregate |
|---|---|---|
| Active Sprint Remaining Points | Pulse Sprint / Status Log | planned − completed for active sprint |
| Sprint Completed % | Pulse Sprint | completed_points / planned_points |
| Spillover Task Count | Task | in active sprint, not Done at report time |
| Overdue Tasks | Task | `exp_end_date < today` and not Completed (derived) |
| Open Tasks | Task | workflow_state not in Done/Cancelled |
| My Open Tasks / Points | Task | filtered by `_assign` = session user |
| My Hours Logged (Week) | Timesheet Detail | sum hours, current user, this week (actuals) |
| Avg Cycle Time | Pulse Cycle Time report | mean cycle days |
| Avg Velocity | Pulse Sprint | mean completed_points over last N |
| Billable Hours (Month) | Timesheet | sum billable hours (actuals) |
| In-Review Count | Task | workflow_state = In Review |

---

## 6. Dashboard Chart configurations

Charts are **Dashboard Chart** records (fixtures). Two supported source types:

- **`chart_type = Report`** — for Script/Query report output (Burndown, Burnup, CFD, Velocity, Cycle/Lead Time, Sprint Report). The chart names the report and the X/Y columns.
- **`chart_type = Count/Sum/Group By`** on a doctype — for simple aggregates (Workload by assignee as Group By on Task `_assign` summing `pulse_story_points`; Tasks by state as Group By on `workflow_state`).

| Chart | Source | chart_type | Render |
|---|---|---|---|
| Sprint Burndown | Pulse Burndown report | Line (2 series) | date × remaining points |
| Sprint Burnup | Pulse Burnup report | Line (2 series) | date × points |
| Velocity | Pulse Velocity report | Bar + avg line | sprint × completed points |
| Cumulative Flow | Pulse Cumulative Flow report | Stacked area | date × count per state |
| Cycle / Lead Time | respective reports | Scatter / Histogram | done date × days |
| Workload by Assignee | Task (Group By `_assign`) | Bar | assignee × open points |
| Tasks by State | Task (Group By `workflow_state`) | Donut | state distribution |

Common config: `timeseries` on time-based charts, `time_interval = Daily`, `filters_json` seeded with the default project/active sprint, `is_public = 0`, role restriction inherited from workspace. Refresh cadence aligned with the snapshot job (§7).

---

## 7. How Burndown Snapshots Are Produced (scheduled job vs on-the-fly)

The burndown/burnup/CFD line for **historical days is deterministic** (past Status Log rows never change), while **today's point moves continuously**. Pulse uses a hybrid:

- **On-the-fly for the current day:** when a user opens the burndown/board, today's remaining is computed live from `Pulse Task Status Log` for the active sprint (small, indexed query filtered by `sprint` + `changed_on`). This gives an always-fresh "now" without waiting for a job.
- **Scheduled daily snapshot for history & performance:** a `scheduler_events` **daily** job (e.g. `pulse.pulse.tasks.snapshot_burndown`, runs just after midnight per site timezone) walks each **Active** sprint and writes one row per state/points figure into the Dashboard Chart cache (or a small summary doctype). This:
  - keeps the chart O(days) instead of re-scanning the whole log on every page load (Analysis §26, §363 scalability guidance — precompute heavy metrics via scheduler, not per render);
  - freezes the ideal line using the Holiday List working-day count fixed at sprint start;
  - is **idempotent** — re-running for a date overwrites that date's snapshot, never duplicates.

The scheduled job **only reads** Status Log and sprint data and **writes derived cache rows** — it never mutates Task state (explicitly avoiding the destructive nightly job from Appendix A4). CFD and burnup reuse the same snapshot pass. If the job is disabled, all charts still work fully on-the-fly (correctness never depends on the job — only performance does).

---

*End of Document 11 of 21.*
