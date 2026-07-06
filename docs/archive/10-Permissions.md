# Pulse — Permissions & Access Control

**Document 10 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 0. Purpose & scope

This document specifies **who can see and do what** in Pulse, and how that is enforced. It is deliberately **reuse-first**: Pulse does **not** ship a custom permission engine. Access control is built entirely on Frappe/ERPNext primitives already listed in the canonical model §2:

> **Role · Role Profile · Has Role · DocPerm · User Permission · permlevel · `permission_query_conditions` · `has_permission` · Workflow transition roles · Document Sharing.**

Pulse adds exactly **one** policy layer on top of these: a **hierarchical assignment rule** (assign-down-only), driven by the `Pulse Role Rank` table in `Pulse Settings` (canonical §3.4, §6). That rule is an *additional constraint on assignment*, never a replacement for DocPerm.

**Non-negotiables (from Analysis §24, §A5):**
- **NEVER** use blanket `ignore_permissions=True` on any user-triggered path. The current build's systemic bypass (Appendix A5) is the exact anti-pattern this document exists to prevent.
- All writes route through the standard document API so `validate`, DocPerm, User Permission and doc-events fire normally.
- Hierarchy is enforced **server-side** (`validate` + `permission_query_conditions`), never UI-only.
- Financial fields are protected by **permlevel**, not by hiding them in the UI.

---

## 1. Role definitions

Seven roles ship as **fixtures** (canonical §6). They are ordinary Frappe Roles; grouping them into a **Role Profile** per persona is recommended so onboarding is one assignment.

| Role | Persona | Core responsibilities | Typical DocType posture |
|---|---|---|---|
| **Pulse Admin** | App owner / system manager for Pulse | Configure `Pulse Settings`, role ranks, workflows, fixtures; manage all projects; full agile + financial visibility. Superset of Manager. | Full CRUD on all Pulse doctypes; permlevel 0 **and** 1 on Task/Project. |
| **Pulse Manager** | Delivery / program manager, PMO | Create & close projects and sprints; plan backlog; assign anyone below; read costing/financials. Owns portfolio health. | CRUD Project/Task/Sprint; read+write permlevel 1 (financials). |
| **Pulse Team Lead** | Scrum master / tech lead | Run sprints (plan→active→close), manage board, assign down to devs/interns, edit tasks in their projects. No financial edit. | CRUD Task; write Sprint status; read-only permlevel 1. |
| **Pulse Senior Developer** | Senior IC | Create/edit tasks, move on board, log time, assign to junior/intern & self, break down stories. | Create/write Task (permlevel 0); no permlevel 1. |
| **Pulse Junior Developer** | IC | Work assigned tasks, move own/assigned cards on board, log time, create sub-tasks, assign to intern & self. | Write assigned Task (permlevel 0); no create Project/Sprint. |
| **Pulse Intern** | Trainee | Work assigned tasks, comment, log time, move own cards. Assign only to self. | Write own assigned Task (permlevel 0), heavily row-scoped. |
| **Pulse Viewer** | Stakeholder / client-side observer | Read-only across permitted projects: boards, backlog, reports, burndown. No writes, no assignment. | Read-only, permlevel 0 only; no financials. |

> Delivery roles (Team Lead and below) never see or edit financial fields. That is guaranteed structurally by **permlevel 1** (§4), not by convention.

---

## 2. Role hierarchy & ranks (canonical §6)

Ranks live in **`Pulse Settings.role_ranks`** (child table **`Pulse Role Rank`**: `role` Link→Role, `rank` Int, higher = more senior). Shipped defaults:

| Role | Rank |
|---|---|
| Pulse Admin | 100 |
| Pulse Manager | 80 |
| Pulse Team Lead | 60 |
| Pulse Senior Developer | 40 |
| Pulse Junior Developer | 20 |
| Pulse Intern | 10 |
| Pulse Viewer | 0 |

**A user's effective rank = the MAX rank across all Pulse roles they hold.** A user with both `Pulse Intern` (10) and `Pulse Team Lead` (60) has effective rank 60.

Ranks are **data, not code** — an admin can re-rank or add custom roles without a deploy. This is the single input to the assignment rule (§7). Ranks do **not** grant DocType access; DocPerm does that. Rank only governs *who may be assigned by whom*.

---

## 3. DocType permission matrix (permlevel 0 unless noted)

Legend: R=read · W=write · C=create · D=delete · S=submit · X=cancel · A=amend. Task/Project/Timesheet/Sprint are **non-submittable** in Pulse's model, so S/X/A are N/A (—). `Pulse Task Status Log` is **append-only** (create by system only; no user write/delete). These are the **DocPerm fixtures** shipped with the app.

### Project
| Role | R | W | C | D | S | X | A | permlevel notes |
|---|---|---|---|---|---|---|---|---|
| Pulse Admin | ✅ | ✅ | ✅ | ✅ | — | — | — | R/W at permlevel 0 **and** 1 |
| Pulse Manager | ✅ | ✅ | ✅ | ❌ | — | — | — | R/W permlevel 0; R/W permlevel 1 |
| Pulse Team Lead | ✅ | ✅ | ❌ | ❌ | — | — | — | permlevel 0 only; R permlevel 1 |
| Pulse Senior Developer | ✅ | ❌ | ❌ | ❌ | — | — | — | permlevel 0 only |
| Pulse Junior Developer | ✅ | ❌ | ❌ | ❌ | — | — | — | permlevel 0 only |
| Pulse Intern | ✅ | ❌ | ❌ | ❌ | — | — | — | permlevel 0 only |
| Pulse Viewer | ✅ | ❌ | ❌ | ❌ | — | — | — | permlevel 0 only |

### Task (the Pulse "card")
| Role | R | W | C | D | S | X | A | permlevel notes |
|---|---|---|---|---|---|---|---|---|
| Pulse Admin | ✅ | ✅ | ✅ | ✅ | — | — | — | R/W permlevel 0 **and** 1 |
| Pulse Manager | ✅ | ✅ | ✅ | ✅ | — | — | — | R/W permlevel 0; R/W permlevel 1 |
| Pulse Team Lead | ✅ | ✅ | ✅ | ❌ | — | — | — | permlevel 0; **R only** permlevel 1 |
| Pulse Senior Developer | ✅ | ✅ | ✅ | ❌ | — | — | — | permlevel 0 only (no financial fields) |
| Pulse Junior Developer | ✅ | ✅ (if_owner/assigned) | ✅ | ❌ | — | — | — | permlevel 0 only |
| Pulse Intern | ✅ | ✅ (if_owner/assigned) | ✅ | ❌ | — | — | — | permlevel 0 only |
| Pulse Viewer | ✅ | ❌ | ❌ | ❌ | — | — | — | permlevel 0 only |

### Pulse Sprint
| Role | R | W | C | D | S | X | A | notes |
|---|---|---|---|---|---|---|---|---|
| Pulse Admin | ✅ | ✅ | ✅ | ✅ | — | — | — | |
| Pulse Manager | ✅ | ✅ | ✅ | ✅ | — | — | — | |
| Pulse Team Lead | ✅ | ✅ | ✅ | ❌ | — | — | — | plan/activate/close |
| Pulse Senior Developer | ✅ | ❌ | ❌ | ❌ | — | — | — | read for board scoping |
| Pulse Junior Developer | ✅ | ❌ | ❌ | ❌ | — | — | — | |
| Pulse Intern | ✅ | ❌ | ❌ | ❌ | — | — | — | |
| Pulse Viewer | ✅ | ❌ | ❌ | ❌ | — | — | — | |

### Pulse Task Status Log (append-only; system-written)
| Role | R | W | C | D | notes |
|---|---|---|---|---|---|
| Pulse Admin | ✅ | ❌ | ❌ | ❌ | audit-only; never edited even by admin |
| Pulse Manager | ✅ | ❌ | ❌ | ❌ | for metrics/reports |
| Pulse Team Lead | ✅ | ❌ | ❌ | ❌ | |
| Pulse Senior/Junior/Intern | ✅ | ❌ | ❌ | ❌ | read for cycle-time reports |
| Pulse Viewer | ✅ | ❌ | ❌ | ❌ | |

> Rows are inserted by the doc-event writer (Automation doc §doc-events) using a narrowly-scoped `frappe.get_doc(...).insert()`. Because no role has create/write DocPerm, the insert path is the **only** writer; the append-only guarantee is enforced by DocPerm, not by trusting callers. This is the *one* place where a controlled `ignore_permissions` on the system insert is acceptable — it is a system event, not a user action, and it writes an immutable audit row. Document it explicitly and cover it with a test.

### Pulse Settings (Single)
| Role | R | W | notes |
|---|---|---|---|
| Pulse Admin | ✅ | ✅ | role ranks, sprint length, toggles |
| Pulse Manager | ✅ | ❌ | read config only |
| All other Pulse roles | ❌ | ❌ | no access to config |

### Timesheet (reused ERPNext doctype — Pulse adds Pulse roles to existing DocPerm; does not redefine ERPNext's own)
| Role | R | W | C | D | S | X | A | notes |
|---|---|---|---|---|---|---|---|---|
| Pulse Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Timesheet is submittable in ERPNext |
| Pulse Manager | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | approve team time |
| Pulse Team Lead | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | review team time |
| Pulse Senior Developer | ✅ (own) | ✅ (own) | ✅ | ❌ | ✅ (own) | ❌ | ❌ | log own hours |
| Pulse Junior Developer | ✅ (own) | ✅ (own) | ✅ | ❌ | ✅ (own) | ❌ | ❌ | log own hours |
| Pulse Intern | ✅ (own) | ✅ (own) | ✅ | ❌ | ❌ | ❌ | ❌ | log; lead submits |
| Pulse Viewer | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | no time access |

> "own" = enforced via `if_owner` DocPerm + User Permission on Employee. Pulse **appends** its roles to Timesheet permissions via fixtures; it must not remove or override ERPNext's stock Timesheet permissions (upgrade-safety, Analysis §17/§20).

---

## 4. Field-level security via permlevel

**Problem:** delivery roles (Team Lead and below) must run the board but must **never** edit costing/rates/margin. **Solution (reuse):** Frappe **permlevel**. Financial fields sit at **permlevel 1**; agile/delivery fields stay at **permlevel 0**. A role gets permlevel-1 access only via an explicit permlevel-1 DocPerm row.

**Fields promoted to permlevel 1 (read-restricted / write-restricted for delivery roles):**

| DocType | Field (examples) | permlevel |
|---|---|---|
| Task | `expected_time` (costing basis), any rate/billing-related custom fields, cost fields | 1 |
| Project | `estimated_costing`, `total_costing_amount`, `total_billable_amount`, `gross_margin`, `per_gross_margin`, `total_billed_amount`, cost-center/rate fields | 1 |
| Timesheet | `billing_rate`, `costing_rate`, `total_billable_amount`, `total_costing_amount` | 1 |

**permlevel access grants:**
- **Read + Write permlevel 1:** Pulse Admin, Pulse Manager.
- **Read-only permlevel 1:** Pulse Team Lead (can *see* project financial health but not change it).
- **No permlevel 1 at all:** Senior/Junior Developer, Intern, Viewer — the fields are invisible and unwritable for them, framework-enforced.

Pulse's own agile fields (`pulse_story_points`, `pulse_sprint`, `pulse_rank`, `pulse_epic`, `pulse_release`) stay at **permlevel 0** so delivery roles can fully operate the board. Do **not** put agile fields at permlevel 1.

> Rationale (Analysis §24, canonical §6): "Financial fields on Task/Project protected via permlevel." permlevel is server-enforced on read, list, and write — hiding a field in JS is not security.

---

## 5. User Permission scoping (row-level restriction by master)

**User Permission** restricts a user's document access by linked master value — no code required. Pulse uses it for multi-project / multi-company / multi-department scoping:

| Scope by | Applied on | Effect |
|---|---|---|
| **Project** | User Permission (user → Project) | User sees only Tasks/Sprints/Status Logs of their permitted Projects. Combined with the query condition (§6), a Team Lead is confined to their projects. |
| **Company** | User Permission (user → Company) | Multi-company tenants isolate projects/timesheets by Company. Reuses ERPNext's company dimension. |
| **Department** | User Permission (user → Department) | Team-based visibility; replaces the deprecated `Pulse Team` (canonical §1 — teams = ERPNext structures). |

Notes:
- **"Apply User Permissions"** must be enabled on the relevant DocPerm rows for the restriction to bite.
- **"Strict User Permissions"** (System Settings) controls whether a missing permission on one doctype blocks or allows — decide per deployment; default to strict for client-facing Viewer accounts.
- Viewers are typically given a **Project** User Permission so a client sees exactly one project's board and reports.
- User Permissions are additive to DocPerm and to the query conditions in §6; the effective visibility is the **intersection**.

---

## 6. `permission_query_conditions` (row-level visibility)

For list/report/board queries, Frappe calls registered `permission_query_conditions` hooks and ANDs the returned SQL into every query. This is where Pulse implements **project-scoped** and **assignment-scoped** visibility beyond plain User Permissions (e.g. "Interns see only tasks assigned to them").

Registered in `hooks.py`:

```python
permission_query_conditions = {
    "Task": "pulse.permissions.task_query_conditions",
    "Pulse Sprint": "pulse.permissions.sprint_query_conditions",
    "Pulse Task Status Log": "pulse.permissions.status_log_query_conditions",
}
```

Pseudocode (returns a SQL WHERE fragment string, parameterized; returns `""` for full-access roles):

```python
def task_query_conditions(user=None):
    user = user or frappe.session.user
    if "Pulse Admin" in roles(user) or "Pulse Manager" in roles(user):
        return ""                       # portfolio-wide; User Permission (§5) still applies
    if "System Manager" in roles(user) or "Administrator" == user:
        return ""

    conditions = []

    # Project scoping: restrict to projects the user may see.
    #   Prefer letting core User Permission handle Project; add an explicit
    #   guard only where User Permissions are not applied on Task DocPerm.
    projects = allowed_projects(user)   # from User Permission cache / Project Users
    if projects is not None:            # None => unrestricted by project
        plist = ", ".join(frappe.db.escape(p) for p in projects)
        conditions.append(f"`tabTask`.`project` in ({plist})")

    # Assignment scoping for the most junior roles: only their own cards.
    if top_role(user) in ("Pulse Junior Developer", "Pulse Intern"):
        # _assign is a JSON array of user ids; use FIND_IN_SET-safe LIKE on the
        # normalized value, or JSON_CONTAINS on MariaDB 10.x.
        u = frappe.db.escape(user)
        conditions.append(
            f"(`tabTask`.`_assign` like {frappe.db.escape('%' + user + '%')} "
            f" or `tabTask`.`owner` = {u})"
        )

    return " and ".join(conditions)
```

Design rules:
- **Return a string, never mutate the query.** Frappe wraps it in the WHERE clause.
- **Always escape** interpolated values (`frappe.db.escape`); no f-string of raw user input.
- Full-access roles return `""` so the query stays fast (no needless subqueries).
- The condition is a **floor**, not a ceiling: it composes (AND) with User Permission (§5) and permlevel (§4). It cannot *grant* access, only *narrow* it.
- `sprint_query_conditions` and `status_log_query_conditions` follow the same shape, scoping by `project` (and, for status log, by the tasks the user may read).

---

## 7. Hierarchical assignment rule (assign-down-only) — full spec

**Policy (canonical §6):** a user may assign a task **only to users whose effective rank ≤ their own effective rank** (down or sideways, never up). Enforced in **two places** so the UI and the API agree, and neither can be bypassed:

1. **Server-side `validate`** on assignment (authoritative gate on write).
2. **Query condition / API filter** feeding the assignee picker (so the UI only *offers* legal targets — UX, not security).

Toggle: honored only when `Pulse Settings.enable_hierarchical_assignment` is checked (default 1).

### 7.1 Rank map

```python
def get_rank_map():
    # Cached; rebuilt on Pulse Settings change (doc-event clears cache).
    settings = frappe.get_cached_doc("Pulse Settings")
    return {row.role: row.rank for row in settings.role_ranks}

def effective_rank(user):
    rmap = get_rank_map()
    user_ranks = [rmap[r] for r in frappe.get_roles(user) if r in rmap]
    return max(user_ranks) if user_ranks else -1   # no Pulse role => cannot be assigned by rule
```

### 7.2 The assignment gate (assign-down-only)

Frappe assignment writes to `ToDo` and the `_assign` field. Pulse hooks the assignment path (ToDo `validate`/`before_insert`, and the Task `validate` that reconciles `_assign`) to enforce rank:

```python
def validate_assignment(assigner, assignee, doc=None):
    if not frappe.get_cached_value("Pulse Settings", None, "enable_hierarchical_assignment"):
        return                                  # feature off => defer to plain DocPerm

    if assigner in ("Administrator",) or "Pulse Admin" in frappe.get_roles(assigner):
        return                                  # admins unconstrained by hierarchy

    a_rank = effective_rank(assigner)
    t_rank = effective_rank(assignee)

    if t_rank > a_rank:
        frappe.throw(_(
            "You cannot assign work to {0}: their role rank ({1}) is higher than yours ({2}). "
            "Assignment is allowed only down or across the hierarchy."
        ).format(assignee, t_rank, a_rank), title=_("Assignment Not Allowed"))
```

Wiring (in `hooks.py` `doc_events`):

```python
doc_events = {
    "ToDo": {
        "before_insert": "pulse.permissions.on_todo_assign",   # calls validate_assignment
        "validate":      "pulse.permissions.on_todo_assign",
    },
    "Task": {
        "validate": "pulse.permissions.validate_task_assignees", # reconciles _assign changes
    },
}
```

`validate_task_assignees` diffs `doc._assign` (new vs `doc.get_doc_before_save()._assign`) and runs `validate_assignment(frappe.session.user, added_user)` for each **newly added** assignee — so bulk `_assign` edits and API writes are covered, not just the ToDo UI path.

### 7.3 Feeding the picker (UX layer)

A whitelisted, permission-checked endpoint returns only legal assignees so the UI never offers an illegal one:

```python
@frappe.whitelist()
def assignable_users(doctype, name):
    frappe.has_permission(doctype, "write", doc=name, throw=True)   # never skip this
    me = frappe.session.user
    my_rank = effective_rank(me)
    if "Pulse Admin" in frappe.get_roles(me):
        return all_active_pulse_users()
    return [u for u in project_members(doctype, name)
            if effective_rank(u) <= my_rank]
```

This is convenience only. If a client crafts a raw request with an illegal assignee, **§7.2 still rejects it** — security is at `validate`, not in the picker.

### 7.4 Properties

- **Deterministic & data-driven:** re-ranking in `Pulse Settings` changes behavior with no deploy.
- **Composable:** runs *in addition* to DocPerm (§3) and User Permission (§5). A user who lacks write on Task can't assign at all, regardless of rank.
- **Auditable:** rejected assignments raise; successful ones flow through standard ToDo/`_assign`, captured in the timeline/Version.
- **No new engine:** it is a `validate` hook + a query filter — exactly what Analysis §14/§18 mandate ("policy over existing perms; extension, no new engine").

---

## 8. Workflow transition permissions

Board columns are **Workflow states** (canonical §5): `Backlog → To Do → In Progress → In Review → Done` (+ `Cancelled`), on the **Task** doctype via **Pulse Task Workflow**. Each transition is gated by an **allowed role** in the Workflow definition — this is reuse of Frappe Workflow, not custom code.

| Transition | Allowed roles (via Workflow Transition `allowed`) |
|---|---|
| Backlog → To Do | Team Lead, Manager, Admin (sprint planning) |
| To Do → In Progress | Senior/Junior Dev, Intern (if assigned), Team Lead+ |
| In Progress → In Review | Senior/Junior Dev, Intern (if assigned), Team Lead+ |
| In Review → Done | Team Lead, Senior Developer, Manager, Admin (review gate) |
| In Review → In Progress (reject) | Team Lead, Senior Developer, Manager, Admin |
| any → Cancelled | Team Lead, Manager, Admin |

Rules:
- **Self-approval guard:** the reviewer role on `In Review → Done` should differ from the implementer where possible; Team Lead/Senior gate the merge to `Done`. Configure via Workflow Transition `condition` (e.g. `doc.owner != frappe.session.user`) where policy requires it.
- Reaching **Done** maps Task `status = Completed` (canonical §5) via workflow field mapping / doc-event, so core costing/closure still fires.
- **"Self Approval Allowed"** and transition **conditions** are set in the Workflow doc — no Python needed for the common cases.
- Workflow permissions are enforced by Frappe on top of DocPerm; a user needs **both** write DocPerm on Task **and** the transition role.

---

## 9. Document sharing

Reuse Frappe **Document Sharing** (`DocShare`) for ad-hoc, per-document grants that sit outside the role model:

- **Use case:** share one Task or one Sprint report with a specific stakeholder (e.g. a client Viewer) without granting a project-wide role.
- **Mechanics:** `frappe.share.add(doctype, name, user, read=1, write=0)` — grants read/write/share on that single document only.
- **Governance:** sharing **read** is safe; granting **write** via share should be restricted to Manager/Admin and logged. Never use share to escape permlevel — a share grants row access, not field-level (permlevel-1) access.
- **Assignment auto-shares:** Frappe's assignment (ToDo) already auto-shares the document with the assignee (read). This is expected and desirable; it means an assignee can always open their card.

---

## 10. Security do / don't

**DO**
- Enforce every permission via **DocPerm + permlevel + User Permission + query conditions + workflow roles** — all reused framework primitives.
- Call `frappe.has_permission(doctype, ptype, doc=..., throw=True)` at the top of **every** whitelisted write endpoint.
- Keep financial fields at **permlevel 1**; grant permlevel 1 only to Admin/Manager (write) and Team Lead (read).
- Enforce the assignment hierarchy in **`validate`** (server), and *also* filter the picker for good UX.
- Parameterize / `frappe.db.escape` everything in `permission_query_conditions`.
- Make `Pulse Task Status Log` append-only via DocPerm; write it only through the system doc-event.
- Ship all roles/DocPerms/permlevels/workflows/ranks as **fixtures** so installs are reproducible and upgrade-safe.

**DON'T**
- **Never** `ignore_permissions=True` on a user-triggered path (Analysis §A5 — the exact defect being retired). The single allowed exception is the immutable Status Log insert (§3), documented and tested.
- Don't hide financial fields in JS and call it security — use permlevel.
- Don't enforce the assignment hierarchy only in the UI picker — a raw API call must still be rejected.
- Don't redefine or strip ERPNext's stock Timesheet/Project permissions — **append** Pulse roles via fixtures; no core edits (Analysis §20).
- Don't build a custom permission/team engine (the deprecated `Pulse Team`, `has_team_permission()` that "always returns True" — Analysis §A5). Use Role + User Permission + Department.
- Don't grant `System Manager` to delivery users to "make it work" — scope with Pulse roles + permlevel.
- Don't let query conditions *grant* access; they can only *narrow*. Grants come from DocPerm/User Permission/Share.

---

*End of Document 10. Next: Document 11 (Data Migration) → Document 12 (Notifications).*
