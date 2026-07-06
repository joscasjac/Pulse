# Pulse — Coding Standards

**Document 19 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26 · App `pulse` · Module `Pulse`
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new. The single most important standard here is the **reuse gate**: *"Does ERPNext/Frappe already do this?"*

---

## 1. Python standards (Frappe conventions)

- **PEP 8 / Frappe style.** Use `frappe` APIs, not raw SQL. Format with **ruff** (see §9).
- **Whitelisting rules.** Expose server methods with `@frappe.whitelist()` deliberately and minimally. Validate every argument. Enforce doc-level permission inside each endpoint with `frappe.has_permission(...)`. Namespace all endpoints under `pulse.api.*` (canonical §11).
- **NEVER blanket `ignore_permissions`.** Writes go through the standard document API (`frappe.get_doc(...).insert()/.save()`) so roles, `permlevel`, doc-events, and validations fire automatically. The old build's systemic `ignore_permissions=True` (Doc 0 Appendix A5) is banned. If a genuinely system-level write is unavoidable, isolate it, comment the justification, and never expose it on a user-triggered path.
- **Parameterized queries only.** Use `frappe.db.get_all/get_value/set_value` and `frappe.qb` (Query Builder). If raw SQL is truly required, use `%(name)s` placeholders — never f-strings/`.format()` with user input (SQL injection).
- **Thin controllers.** Doctype controllers hold validation and light derivation only. No fat service layer re-implementing framework behavior (assignment, notifications, permissions) — that was the old build's mistake. Metrics live in small, pure, tested functions.
- **Doc-event patterns.** Prefer `doc_events` hooks (`validate`, `on_update`, `on_submit`) over ad-hoc calls. The status-log writer is an `on_update` event; the hierarchy check is a `validate`/assignment hook. Keep events idempotent and fast; offload heavy work to the scheduler.
- **No permission bypass; no `frappe.db.commit()` inside request handlers** (let the framework manage the transaction).

Example — a correct thin whitelisted endpoint:

```python
# pulse/api/board.py
import frappe

@frappe.whitelist()
def get_board(project: str, sprint: str | None = None):
    """Return a lean card payload for the board. Permissions enforced by get_all."""
    if not frappe.has_permission("Project", "read", doc=project):
        frappe.throw("Not permitted", frappe.PermissionError)
    filters = {"project": project}
    if sprint:
        filters["pulse_sprint"] = sprint
    return frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "subject", "workflow_state",
                "pulse_story_points", "pulse_rank", "_assign"],
        order_by="pulse_rank asc",
        limit_page_length=0,
    )
```

---

## 2. JS / Vue + frappe-ui standards

- **Phase 2 SPA:** Vue 3 (Composition API) + **frappe-ui** components; TypeScript preferred; served at `/pulse` (Gameplan/Helpdesk pattern).
- **Central API client.** One typed client wrapping `frappe.call`/frappe-ui resources — no scattered `fetch`. Endpoints correspond to `pulse.api.*`.
- **No business logic duplicated from the server.** The server is authoritative for permissions, rank rules, and metrics; the client renders and optimistically updates, then reconciles.
- **Componentized & typed.** Small components; props typed; use frappe-ui primitives before hand-rolling; respect ERPNext theming and the small Pulse design system.
- **Optimistic UI with reconcile** for drag/reorder; debounce rank persistence.
- **Accessibility:** keyboard nav, ARIA on board/DnD, contrast (analysis §21).
- Legacy Desk JS (bundles) follows Frappe client-script conventions; format with **prettier** (§9).

---

## 3. Doctype & fixture conventions

- **Only four new doctypes:** `Pulse Sprint`, `Pulse Task Status Log`, `Pulse Settings` (single), `Pulse Role Rank` (child) — all in module **Pulse**. Adding any other doctype requires updating `_canonical-model.md` first.
- **Extend via Custom Fields**, not new tables. Custom fields use the `pulse_*` prefix and ship as fixtures.
- **Statuses via Workflow** ("Pulse Task Workflow"), not a custom status field. **Issue types via Task Type**, not a custom type field.
- **Fixtures** (custom fields, Task Types, workflow, roles, charts, number cards, Pulse Settings defaults, Role Ranks) are declared in `hooks.py` and filtered narrowly so no unrelated site data leaks. Re-export + diff on every release (Doc 18).
- **Read-only/append-only** where required: Pulse Task Status Log rows are never user-editable (permlevel/read-only perms).
- **Idempotent installs/patches:** guard fixture/data creation so re-runs are safe.

---

## 4. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| App | lowercase | `pulse` |
| Module | title | `Pulse` |
| Doctype | `Pulse <Name>` | `Pulse Sprint` |
| Custom field | `pulse_*` snake_case | `pulse_story_points` |
| Role | `Pulse <Role>` | `Pulse Team Lead` |
| API namespace | `pulse.api.*` | `pulse.api.board.get_board` |
| Workflow | `Pulse Task Workflow` | — |
| Python module/file | snake_case | `pulse/api/board.py` |
| Vue component | PascalCase | `SprintBoard.vue` |
| Git branch | `feature/…`, `hotfix/…` | `feature/p1-sprint-doctype` |

---

## 5. Docstrings

- Every whitelisted method and every metric function has a docstring: purpose, params, returns, and — for metrics — **the agile formula** (e.g., "velocity = sum of story points of Tasks whose Status Log shows a transition to Done within the sprint window").
- Non-obvious validations (one-active-sprint, hierarchy rank rule) document the business rule and cite `_canonical-model.md` section.

```python
def compute_velocity(sprint: str) -> float:
    """Velocity = completed story points for a sprint.

    Sums ``points_at_change`` from Pulse Task Status Log rows whose
    ``to_state == 'Done'`` within the sprint's date window.
    See _canonical-model.md §8. Pure function; unit-tested.
    """
```

---

## 6. Commit message convention

**Conventional Commits:** `type(scope): summary`.

- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.
- Scope = area: `sprint`, `board`, `metrics`, `hierarchy`, `migration`, `fixtures`.
- Breaking changes: `!` and a `BREAKING CHANGE:` footer (drives SemVer MAJOR, Doc 18).

```
feat(sprint): enforce one active sprint per project

Adds validate() rejecting a second Active Pulse Sprint per project.
See _canonical-model.md §3.1.
```

---

## 7. PR checklist (including the reuse gate)

Every PR must confirm:

- [ ] **Reuse gate:** *Did you check ERPNext/Frappe already does this?* Explain what was reused vs. extended vs. built, and why a build was unavoidable.
- [ ] No new doctype unless `_canonical-model.md` was updated first.
- [ ] No `ignore_permissions=True` on user paths; writes via document API.
- [ ] No raw SQL with interpolated user input (parameterized only).
- [ ] No core ERPNext/Frappe file edits; no monkey-patching core doctypes.
- [ ] Custom fields use `pulse_*`; fixtures updated + filtered + diffed.
- [ ] Tests added/updated (unit for bespoke logic; integration for seams); CI green.
- [ ] Docstrings for new whitelisted methods / metric formulas.
- [ ] Lint/format clean (ruff + prettier).
- [ ] Docs/CHANGELOG updated if user-facing.
- [ ] Conventional Commit messages; breaking changes flagged.

---

## 8. Folder structure rules

```
pulse/
├── pulse/
│   ├── __init__.py            # __version__
│   ├── hooks.py               # fixtures, doc_events, scheduler, required_apps
│   ├── api/                   # thin whitelisted endpoints (pulse.api.*)
│   │   ├── board.py
│   │   └── sprint.py
│   ├── pulse/doctype/         # the four new doctypes (+ tests beside each)
│   │   ├── pulse_sprint/
│   │   ├── pulse_task_status_log/
│   │   ├── pulse_settings/
│   │   └── pulse_role_rank/
│   ├── hooks_impl/            # doc-event handlers (status log writer, hierarchy)
│   ├── metrics/               # pure metric functions (velocity, burndown, ...)
│   ├── fixtures/              # exported fixtures (custom fields, task types, ...)
│   ├── patches/ + patches.txt # idempotent migrations (incl. legacy Pulse* -> core)
│   ├── tests/                 # cross-cutting test suites + factory helpers
│   └── public/ + www/pulse/   # SPA (Phase 2)
├── CHANGELOG.md
├── README.md
└── pyproject.toml             # ruff config, deps
```

Rules: doctype code + tests live together; pure logic (metrics) separated from doc-events for testability; API layer stays thin; fixtures are generated, not hand-authored where the framework can export them.

---

## 9. Linting / formatting

- **Python:** `ruff` (lint + format) via `pyproject.toml`; run `ruff check` + `ruff format` in pre-commit and CI.
- **JS/Vue/JSON/MD:** `prettier` (`prettier --check` in CI).
- **pre-commit** hooks run both locally; CI re-runs them as a merge gate (Doc 16 §10).
- No warnings suppressed globally; justify any inline `# noqa` with a reason.

---

## 10. Anti-patterns to avoid

These caused the original build's failures (Doc 0 §7b, Appendix A) — they are hard bans:

- **Parallel doctypes.** Never re-create a work-item/project table. The card **is** a Task; the project **is** a Project. No `Pulse Task`/`Pulse Project`/`Pulse Team`/`Pulse Milestone`/`Pulse Label`, etc.
- **Permission bypass.** No blanket `ignore_permissions=True`; no permission hook that always returns `True`; no unfiltered cross-project queries (info disclosure).
- **Core edits / monkey-patching.** No editing ERPNext/Frappe source; no runtime patching of core doctypes/methods. Everything via fixtures, custom fields, doc-events, workflow, permission hooks.
- **Re-implementing framework plumbing.** Don't hand-roll assignment, notifications, comments, audit, or REST auth — reuse Frappe's.
- **Destructive scheduled jobs.** Never force-write user data (the old nightly "set status = In Progress" job, Doc 0 A4). Derived indicators, not forced writes.
- **Duplicated logic / race conditions.** Compute a rollup in exactly one place (the old build computed task counts in two, Doc 0 A7).
- **Fat controllers / service classes** that duplicate framework behavior.
- **Raw string-interpolated SQL.**
- **Wrong field-name coupling / shadow sync** — obviated by the card being the Task (no sync needed; Doc 0 A3).

*End of Document 19.*
