# Pulse — Automation

**Document 13 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. Automation philosophy

Pulse automates through Frappe's existing machinery (canonical §2, Analysis §16, §57 principle "the framework does the plumbing"):

- **Scheduler** (`scheduler_events` in `hooks.py`) — cron/daily/hourly background jobs.
- **doc-events** (`doc_events` in `hooks.py`) — synchronous hooks on document lifecycle (validate, on_update, on_submit, etc.).
- **Assignment Rule** (Frappe core doctype) — round-robin / load-balanced auto-assignment, config-only.
- **Auto Repeat** (Frappe core doctype) — recurring documents (recurring tasks/templates).

Pulse writes **no bespoke scheduler or assignment engine** — the current build's parallel `pulse/scheduled/*` and `pulse/services/*` are retired (Analysis §7b, §A4, §A5). Automation code is thin: each doc-event handler and each scheduled job is a small, pure, tested function.

**Two hard rules carried from the analysis:**
1. **Overdue is a derived INDICATOR, never a status overwrite.** The old daily `UPDATE ... SET status='In Progress'` job (Analysis §A4) is explicitly **deleted**. Overdue is computed for display + notified (Notifications N6); it never mutates `status`/`workflow_state`.
2. **No destructive auto-writes.** Automation appends (Status Log), caches (metrics), and notifies. It does not silently rewrite user-entered data.

---

## 2. Scheduled jobs

Registered in `hooks.py`:

```python
scheduler_events = {
    "daily": [
        "pulse.tasks.scheduled.close_sprints_reaching_end_date",
        "pulse.tasks.scheduled.snapshot_burndown",
        "pulse.tasks.scheduled.refresh_project_stats_cache",
        "pulse.tasks.scheduled.refresh_overdue_indicator_cache",
    ],
    "hourly_long": [
        # heavy metric recompute if a project has opted into hourly freshness
    ],
}
```

| Job | Frequency | Purpose | Implementation |
|---|---|---|---|
| **Overdue indicator refresh** | Daily (early) | Recompute the *derived* "is overdue" flag/count for boards & dashboards. **Never writes `status`.** | Query Tasks where `exp_end_date < today()` AND `workflow_state not in (Done, Cancelled)`; write only to a **cache** (Redis / a `pulse_is_overdue` display value or a Number Card cache), **not** to the task's status. Idempotent, read-mostly. Replaces the deleted destructive job (Analysis §A4). |
| **Sprint auto-close** | Daily | Close sprints whose `end_date < today()` and still `Active`. | For each such `Pulse Sprint`: set `status=Completed`, compute `completed_points`/`velocity`, fire the close doc-event (spillover + N4/N8 notifications). Guarded so it runs once per sprint (skip if already Completed). No task statuses are forced. |
| **Daily burndown snapshot** | Daily (after close) | Persist one remaining-points datapoint per active sprint per day for burndown/burnup/CFD, derived from Status Log. | For each Active sprint: compute remaining points as of `today()` from **Pulse Task Status Log** + sprint membership + working days (`Pulse Settings.working_days_source` Holiday List). Write to a **snapshot cache** (Dashboard Chart cache or a lightweight summary rows keyed by sprint+date). Append-only per day; re-run overwrites *today's* row only (idempotent). |
| **Project stats cache** | Daily | Precompute per-project rollups (open/closed counts, points, % complete, active sprint) so boards/dashboards don't recompute per request (Analysis §25/§26). | Aggregate over Task; store in cache / Number Card cache. Read-only source; never edits Task/Project business fields. |

Notes:
- All jobs are **idempotent** and safe to re-run (Analysis §23 "idempotent installs/migrations").
- Heavy metric math is **precomputed here**, not on page load (Analysis §26).
- Jobs read with permissions in mind but run as scheduler; they must **not** leak data into user-visible caches across project boundaries.

---

## 3. doc-events

Registered in `hooks.py` `doc_events`:

```python
doc_events = {
    "Task": {
        "validate":  "pulse.doc_events.task.validate",       # assignee-rank check (Permissions §7)
        "before_insert": "pulse.doc_events.task.assign_rank",
        "on_update": "pulse.doc_events.task.on_update",       # status-log writer + Done→status sync + rollup trigger
    },
    "Pulse Sprint": {
        "validate":  "pulse.doc_events.sprint.validate",     # one Active sprint per project
        "on_update": "pulse.doc_events.sprint.on_update",     # start/close notifications, velocity at close
    },
    "ToDo": {
        "before_insert": "pulse.permissions.on_todo_assign",  # hierarchical assignment gate (Permissions §7)
    },
}
```

| Doctype | Event | Handler | Action |
|---|---|---|---|
| **Task** | `on_update` (workflow/status change) | `task.on_update` → status-log writer | If `workflow_state` (or `status`) changed vs `get_doc_before_save()`, insert an **immutable Pulse Task Status Log** row (`task`, `project`, `sprint`, `from_state`, `to_state`, `changed_by`, `changed_on`, `points_at_change`). Append-only; the *only* writer of that doctype (Permissions §3). Powers burndown/CFD/cycle-time. |
| **Task** | `on_update` reaching `Done` | `task.on_update` → Done sync | When `workflow_state == "Done"`, set Task `status = "Completed"` (canonical §5) so core costing/closure fires. Also triggers dependency-unblocked check (Notifications N7). Guarded to run once on the transition. |
| **Task** | `before_insert` | `task.assign_rank` | Set `pulse_rank` on create (backlog ordering) — e.g. append to end of the project/backlog (`max(pulse_rank)+step`). Deterministic; no gaps required. (This is the field `pulse_rank`, not the role rank.) |
| **Task** | `validate` | `task.validate` | Enforce hierarchical **assignee** rank (Permissions §7.2) on `_assign` diffs; run *in addition* to DocPerm. |
| **Task** | `on_update` (points/state) | `task.on_update` → rollup trigger | On story-point or Done change, enqueue/trigger sprint rollup (below). Debounced to avoid churn. |
| **Pulse Sprint** | rollup | `sprint` rollup | Recompute `planned_points` (sum of member-task points) and `completed_points` (sum of points for tasks in `Done`); set `velocity = completed_points` at close. Read from Task; write only the Sprint's computed read-only fields. |
| **Pulse Sprint** | `validate` | `sprint.validate` | Enforce **one Active sprint per project** (`is_active`), validate date order. |
| **Pulse Sprint** | `on_update` (status transition) | `sprint.on_update` | On `Active` → sprint-started notification (N3); on `Completed` → compute velocity/spillover, fire N4/N8. |
| **ToDo** | `before_insert` | `permissions.on_todo_assign` | Hierarchical assignment gate (assign-down-only, Permissions §7). |

Notes:
- **`pulse_rank` (role rank) vs `pulse_rank` (backlog rank):** the *role* rank lives in `Pulse Role Rank` (Settings) and governs assignment (Permissions §7); the *backlog* `pulse_rank` custom field on Task governs ordering. Assignment on Task create refers to backlog rank; the assign-down check refers to role rank. Keep the distinction explicit in code comments.
- Status-log write and Done→status sync are the two most important handlers; both are **idempotent** (compare before/after, act only on real transitions).

---

## 4. Assignment Rules (round-robin / load-balance)

Reuse Frappe **Assignment Rule** (core doctype) — **no custom auto-assign code**:

- **Round-robin:** auto-assign new tasks in a project cyclically across a user list. Config: Assignment Rule with `document_type = Task`, `rule = Round Robin`, `assign_condition` (e.g. `project == 'X' and workflow_state == 'To Do'`), and a `users` list.
- **Load balancing:** `rule = Load Balancing` assigns to the user with the fewest open ToDos — good for triage queues.
- **Interaction with hierarchy:** Assignment Rule auto-assignment still passes through the ToDo `before_insert` gate (Permissions §7). Ensure the rule's user pool respects rank, or rank-rejected auto-assigns will error; recommended to scope Assignment Rule `users` to legal targets. Document this coupling.
- Ships as **fixtures** where a default triage rule is desired; otherwise configured per project by a Manager. Config-only, upgrade-safe.

---

## 5. Auto-repeat / recurring tasks

Reuse Frappe **Auto Repeat** for recurring work (standups, weekly maintenance, recurring project tasks):

- Attach Auto Repeat to a **Task** (or a **Project Template**) with a frequency (daily/weekly/monthly) and end date.
- Frappe generates the next document automatically on schedule — Pulse adds nothing.
- For recurring *project structures*, prefer **Project Template / Project Template Task** (canonical §2) instantiated on a schedule, over hand-built loops.
- New recurring tasks flow through the same doc-events (rank assignment, status log on first transition), so they behave identically to hand-created cards.

---

## 6. Escalations

Escalations reuse the **Notification doctype (Days After)** + optional **Assignment Rule reassignment**, not custom timers:

- **Overdue escalation:** Notification (Days After `exp_end_date`) to assignee at day 0, escalate to Team Lead at day +2, Manager at day +5 — three Notification docs with increasing recipient seniority (Notifications N6 family). Purely notification; **no status change**.
- **Stuck-in-review escalation:** Notification (Days After entering `In Review`, using Status Log-derived date or a value-change + days offset) pinging the reviewer, then Team Lead.
- **Reassignment on inactivity (optional):** an Assignment Rule or a light scheduled job may *propose* reassignment, but must not silently reassign without notification and must respect the assignment hierarchy.

---

## 7. Guardrails

- **Idempotency:** every scheduled job and doc-event is safe to run twice — compare against prior state (`get_doc_before_save`, "already Completed?", "today's snapshot exists?") and no-op if nothing changed.
- **No destructive auto-writes:** automation appends (Status Log), caches (metrics/overdue), computes read-only rollups (sprint points/velocity), and notifies. It never rewrites user-entered `status`, points, dates, or assignments without an explicit, audited trigger. The deleted overdue-status job (Analysis §A4) is the canonical example of what is forbidden.
- **Audit trail:** state transitions are recorded in **Pulse Task Status Log** (immutable) and Frappe **Version**/timeline; sprint close records velocity. Automation actions are traceable.
- **Permission-aware:** doc-events run in the user's context and respect DocPerm/hierarchy; scheduler jobs run as system but must not surface cross-project data into shared caches. No blanket `ignore_permissions` (Analysis §A5) — the single controlled exception is the immutable Status Log insert (Permissions §3), documented and tested.
- **Failure isolation:** notification/webhook sends and metric caching are wrapped so a failure logs (`frappe.log_error`) and never rolls back the user's transaction; heavy work is `frappe.enqueue`d.
- **Thin & tested:** each handler is a small pure function with unit tests for the status-log writer, sprint rollup, hierarchy gate, and burndown math (Analysis §20 "test the extensions, not the framework").

---

*End of Document 13. Next: Document 14 (Reports & Metrics).*
