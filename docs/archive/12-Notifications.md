# Pulse — Notifications

**Document 12 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. Notification philosophy

Pulse sends **zero** notifications through a custom notification system. Everything reuses Frappe's built-in stack (canonical §2, Analysis §16):

- **Notification doctype** — declarative, config-driven alerts (event = New/Save/Submit/Value Change/Days After/Days Before/Method) with conditions, recipients, channel, and a Jinja subject/message. **This is the default choice** — it is data, ships as a fixture, is upgrade-safe, and needs no Python.
- **Email** — via `frappe.sendmail` and the Email Queue/Email Account already configured in the site. The Notification doctype uses this transport automatically.
- **Desktop / in-app** — Frappe's **Notification Log** bell + real-time (`frappe.publish_realtime`) delivery. The Notification doctype can post to the in-app feed; assignment/mention already do this natively.
- **Notification Settings** (per user) — Frappe's own per-user preferences (email digests, mute types, notify-on-mention, etc.). Pulse **respects** these; it does not build a parallel preference store. `Pulse Settings` only holds coarse global toggles (`email_notifications`, `desktop_notifications`, canonical §3.3).

**Decision rule for each notification (applied in §3):**
> If it is a **field-value change, a date-relative reminder, or a simple record event** → use the **Notification doctype** (no code).
> If it needs **aggregation, computed recipients, external channels, or logic** (digests, spillover math, dependency graphs) → use a **doc-event / scheduled method** calling `frappe.sendmail` + `frappe.publish_realtime` (or `notify` helpers).

Assignment and @-mention are **already delivered by Frappe out of the box** — Pulse must **not** re-implement them (Analysis §A5 lesson). We only *configure/augment* them.

---

## 2. Notification catalog

| # | Event | Trigger | Recipients | Channel(s) | Template | Config / Implementation |
|---|---|---|---|---|---|---|
| N1 | **Task assigned** | ToDo/`_assign` created on a Task | New assignee | Email + Desktop (in-app) | `pulse_task_assigned` | **Native Frappe assignment** — already fires email + bell. Reuse as-is; optionally style the email. No Notification doc needed. |
| N2 | **Mention in comment** | `@user` in a Task/Sprint comment | Mentioned user(s) | Email + Desktop | `pulse_mention` (Frappe default) | **Native Frappe mention** notification. Reuse as-is; respect user's "notify on mention" setting. |
| N3 | **Sprint started** | `Pulse Sprint.status` → `Active` | All members of the sprint's project (`_assign` on sprint tasks + project users) | Email + Desktop | `pulse_sprint_started` | **doc-event** `Pulse Sprint.on_update` (detect status transition) → `frappe.sendmail` to computed list + realtime. Recipients are computed → not a plain Notification doc. |
| N4 | **Sprint ended / closed** | `Pulse Sprint.status` → `Completed` (manual or auto-close job) | Project members + Manager/Team Lead | Email + Desktop | `pulse_sprint_ended` | **doc-event** on close; includes velocity & spillover summary (computed) → `frappe.sendmail`. |
| N5 | **Task moved to In Review** | `workflow_state` → `In Review` | Reviewers (Team Lead + Senior Devs on project), task owner | Email + Desktop | `pulse_in_review` | **Notification doctype**, event = *Value Change* on `workflow_state`, condition `doc.workflow_state == "In Review"`, recipients via role + a Jinja recipient expression. Pure value-change → no code. |
| N6 | **Task overdue** | `exp_end_date < today()` and not Done/Cancelled | Current assignees + Team Lead | Email + Desktop | `pulse_overdue` | **Notification doctype**, event = *Days After* on `exp_end_date` (value 0/1), condition excludes Done/Cancelled. Date-relative → no code. (This only *notifies*; it never changes status — see Automation doc, the overdue-indicator fix.) |
| N7 | **Dependency unblocked** | A task's last blocking dependency (`depends_on`) reaches Done | Assignees of the now-unblocked task | Email + Desktop | `pulse_unblocked` | **doc-event** on Task Done: find dependents whose all `depends_on` are complete → notify. Requires graph logic → code path. |
| N8 | **Sprint spillover** | At sprint close, tasks not Done are carried/flagged | Task owner, Team Lead, Manager | Email (+ in digest) | `pulse_spillover` | **doc-event** within the sprint-close handler (same pass as N4). Computed list of spilled tasks → `frappe.sendmail`. |
| N9 | **Daily digest** | Scheduler, daily (per user's Notification Settings) | Each opted-in user | Email | `pulse_daily_digest` | **Scheduled job** (Automation doc) aggregating my open tasks, due-today, mentions, in-review awaiting me → single `frappe.sendmail`. Aggregation → must be code. Respects Frappe's per-user digest preference. |

Channel policy: **Email** honors `Pulse Settings.email_notifications` (global) AND the user's Frappe Notification Settings. **Desktop/in-app** honors `Pulse Settings.desktop_notifications`. Optional **Slack/webhook** (§6) is off by default.

---

## 3. Implementation-by-reuse: recommendation per notification

| # | Recommended mechanism | Why |
|---|---|---|
| N1 Assigned | **Reuse native assignment** (no config) | Frappe already emails + posts in-app on `_assign`; re-implementing was the Appendix-A defect. |
| N2 Mention | **Reuse native mention** (no config) | Built into Comment/Communication; respects user setting. |
| N3 Sprint started | **doc-event + `frappe.sendmail`** | Recipient set is computed (project membership); not expressible as a static Notification doc. |
| N4 Sprint ended | **doc-event + `frappe.sendmail`** | Needs computed velocity/spillover body. |
| N5 In Review | **Notification doctype (Value Change)** | Pure field transition; zero code; ships as fixture. |
| N6 Overdue | **Notification doctype (Days After)** | Date-relative, declarative; **notify only**, never write status. |
| N7 Unblocked | **doc-event** | Dependency-graph evaluation needs logic. |
| N8 Spillover | **doc-event (in close handler)** | Computed list; piggybacks on N4's pass. |
| N9 Daily digest | **Scheduled method + `frappe.sendmail`** | Aggregation across doctypes; respects Notification Settings digest opt-in. |

Guideline: **prefer the Notification doctype** (N5, N6) whenever the trigger is a value change or date offset — it is upgrade-safe config. Drop to a doc-event/scheduled method (N3, N4, N7, N8, N9) only when recipients or body must be **computed**.

All computed-recipient sends must still **respect permissions and preferences**: filter recipients to users who can read the document, and skip users who muted the type in Notification Settings.

---

## 4. Templates (Jinja subject/body)

Templates ship as fixtures (Notification doctype's `subject`/`message`, or `.html` files rendered via `frappe.render_template` in doc-event handlers). Context objects: `doc`, `frappe.session.user`, and helper values passed by the handler.

**N1 — Task assigned** (native; shown for reference)
```
Subject: [Pulse] You've been assigned: {{ doc.subject }}
Body:
Hi {{ assigned_to }},
{{ assigned_by }} assigned you a task in {{ doc.project }}.

Task: {{ doc.subject }}
Priority: {{ doc.priority }} · Due: {{ doc.exp_end_date or "—" }}
Sprint: {{ doc.pulse_sprint or "Backlog" }} · Points: {{ doc.pulse_story_points or "—" }}

Open: {{ frappe.utils.get_url_to_form("Task", doc.name) }}
```

**N3 — Sprint started**
```
Subject: [Pulse] Sprint started: {{ doc.sprint_name }} ({{ doc.project }})
Body:
Sprint "{{ doc.sprint_name }}" is now Active.
Goal: {{ doc.goal or "—" }}
Dates: {{ doc.start_date }} → {{ doc.end_date }}
Planned points: {{ doc.planned_points }}

Open the board: {{ get_url_to_form("Pulse Sprint", doc.name) }}
```

**N4 — Sprint ended**
```
Subject: [Pulse] Sprint completed: {{ doc.sprint_name }} — velocity {{ doc.velocity }}
Body:
Sprint "{{ doc.sprint_name }}" closed on {{ doc.end_date }}.
Planned: {{ doc.planned_points }} · Completed: {{ doc.completed_points }} · Velocity: {{ doc.velocity }}
{% if spillover %}Spilled to backlog/next sprint: {{ spillover|length }} task(s).{% endif %}

Sprint report: {{ report_url }}
```

**N5 — Task moved to In Review**
```
Subject: [Pulse] Review requested: {{ doc.subject }}
Body:
{{ doc.subject }} ({{ doc.project }}) moved to In Review by {{ doc.modified_by }}.
Points: {{ doc.pulse_story_points or "—" }} · Assignees: {{ doc._assign }}

Review: {{ frappe.utils.get_url_to_form("Task", doc.name) }}
```

**N6 — Overdue**
```
Subject: [Pulse] Overdue: {{ doc.subject }} (due {{ doc.exp_end_date }})
Body:
{{ doc.subject }} in {{ doc.project }} is past its due date ({{ doc.exp_end_date }})
and is still {{ doc.workflow_state or doc.status }}.

This is a reminder — the task status has NOT been changed automatically.
Open: {{ frappe.utils.get_url_to_form("Task", doc.name) }}
```

**N7 — Dependency unblocked**
```
Subject: [Pulse] Unblocked: {{ doc.subject }} is ready to start
Body:
All dependencies of "{{ doc.subject }}" ({{ doc.project }}) are now complete.
You can begin work.
Open: {{ frappe.utils.get_url_to_form("Task", doc.name) }}
```

**N8 — Spillover**
```
Subject: [Pulse] Spillover from {{ sprint.sprint_name }}: {{ tasks|length }} task(s)
Body:
These tasks did not complete in {{ sprint.sprint_name }} and were carried over:
{% for t in tasks %}- {{ t.subject }} ({{ t.pulse_story_points or 0 }} pts){% endfor %}
```

**N9 — Daily digest**
```
Subject: [Pulse] Your day — {{ frappe.utils.today() }}
Body:
Due today ({{ due_today|length }}):
{% for t in due_today %}- {{ t.subject }} ({{ t.project }}){% endfor %}
Awaiting your review ({{ in_review|length }}):
{% for t in in_review %}- {{ t.subject }}{% endfor %}
New mentions: {{ mentions|length }} · Overdue: {{ overdue|length }}
Open Pulse: {{ frappe.utils.get_url() }}/app/pulse
```

---

## 5. User preferences

Reuse Frappe **Notification Settings** (per-user Single-per-user doctype). Pulse does **not** duplicate it:

- **Email on assignment / mention / energy points** — Frappe's own toggles; honored automatically by native N1/N2.
- **Mute specific notification types** — users can mute Pulse notification types; computed-recipient handlers (N3, N4, N7, N8, N9) must check `is_notifications_enabled(user)` / respect muted types before sending.
- **Daily digest opt-in** — N9 only sends to users who have digest enabled.
- **Global kill switches** — `Pulse Settings.email_notifications` and `desktop_notifications` gate all Pulse-originated sends site-wide (checked first in every handler).

Precedence when deciding to send: `Pulse Settings global toggle` **AND** `user Notification Settings` **AND** `user can read the document`. If any is false → skip that recipient.

---

## 6. Optional Slack / webhook

Off by default; opt-in per deployment. Reuse, don't build a client:

- **Frappe Webhook doctype** — declaratively POST on Sprint status change or Task Done to a Slack incoming-webhook or generic endpoint. Config-only, upgrade-safe. Preferred.
- **Notification doctype channel = "Slack"** — Frappe supports a Slack channel with a configured Slack Webhook URL; use for simple per-event pings.
- For richer payloads (blocks, threads), a thin doc-event handler may `frappe.integrations`/`requests.post` to the webhook URL stored in `Pulse Settings` — behind a feature flag, with failures logged (`frappe.log_error`) and never blocking the transaction.

No Slack SDK, no custom OAuth — reuse the Webhook doctype and site-configured secrets.

---

## 7. Notes & guardrails

- **Never block the save** on a notification failure — sends happen in the doc-event *after* commit or via `frappe.enqueue` for heavier bodies (digest, spillover); wrap external calls in try/except + `frappe.log_error`.
- **Idempotency:** status-transition notifications (N3, N4, N5) must fire only on the *actual* transition — compare against `doc.get_doc_before_save()`; don't re-notify on unrelated saves.
- **Permission-safe recipients:** computed lists are filtered to users with read access (mirrors Permissions doc §6) — no cross-project information leak (the Appendix-A `get_recent_activity` leak is the anti-pattern).
- **Fixtures:** N5 and N6 Notification docs, and any Slack Webhook config, ship as fixtures for reproducible installs.

---

*End of Document 12. Next: Document 13 (Automation).*
