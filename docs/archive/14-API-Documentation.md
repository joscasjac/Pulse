# Pulse — API Documentation

**Document 14 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. API Design Principles

Pulse's back-end is **thin by mandate**. The framework already provides authentication, sessions, CSRF, permissions, validation, doc-events, and a full REST layer — Pulse must not re-implement any of it (Analysis §57, §313; Canonical §11).

1. **Thin, whitelisted `pulse.api.*` endpoints only where the generic REST API is insufficient.** Custom endpoints exist for two reasons only: (a) returning a **lean, purpose-built payload** for a screen (board, backlog) to avoid N+1 and over-fetching, or (b) orchestrating a **multi-step agile transaction** (start/close sprint). Everything else uses Frappe's generic REST.
2. **Lean payloads.** Board/backlog endpoints return only the fields a card needs (id, title, state, points, assignees, rank) — never the full Task document. Field pruning + server-side filtering + pagination (Analysis §210, §362, §369).
3. **Writes go through the standard Frappe document API and permissions.** `frappe.get_doc(...).save()` / `frappe.client` so `validate`, doc-events (Status Log), workflow transitions, and permission checks all fire normally.
4. **NEVER blanket `ignore_permissions=True`.** This is the single most important rule — it is the root security defect of the old build (Appendix A5, where every write endpoint bypassed permissions). Every endpoint enforces access with `frappe.has_permission(...)` (raising `frappe.PermissionError`) before touching data, and all writes run as the session user. There is no service layer that silently escalates privilege.
5. **Standard Frappe permissions + Pulse hierarchy.** Base access = DocPerm/User Permission. Assignment adds the hierarchical-rank constraint (Canonical §6), enforced server-side in `validate`, never UI-only.
6. **Versioning.** The namespace is versioned by module path stability: endpoints live under `pulse.api.<domain>.<fn>`. Breaking changes ship a new function name (e.g. `get_board_v2`) rather than mutating an existing contract; the old contract is deprecated with a release-note window (Analysis §319, §475).
7. **Actuals are never accepted from the client.** No endpoint writes "actual hours." Actuals come only from Timesheet, entered through standard ERPNext (Canonical §2, §8).

---

## 2. Authentication

Pulse reuses Frappe auth entirely — **no custom auth, no custom session** (Analysis §244, §352; Canonical §42).

- **Session cookie (browser / SPA):** the frappe-ui SPA calls endpoints with the logged-in session cookie. **CSRF token required** for state-changing (`POST`) calls — the SPA sends `X-Frappe-CSRF-Token` (available as `frappe.boot.csrf_token`). `frappe.call` handles this automatically.
- **Token auth (server-to-server / integrations):** `Authorization: token <api_key>:<api_secret>`. Token requests are CSRF-exempt.
- **Permissions** are evaluated for the authenticated user on every call — identical rules across Desk, SPA, and REST.

---

## 3. Reuse of Frappe REST (generic CRUD) vs Custom Endpoints

**Prefer the generic REST API** for straightforward CRUD. It is already permission-safe, filterable, and paginated.

| Need | Use generic REST | Endpoint |
|---|---|---|
| Read/list Tasks (cards) | ✅ | `GET /api/resource/Task?filters=...&fields=...&limit_page_length=...` |
| Create/update a Task field (title, points, dates) | ✅ | `POST/PUT /api/resource/Task` |
| Read/update a Project | ✅ | `/api/resource/Project` |
| List/read a Sprint | ✅ | `/api/resource/Pulse Sprint` |
| Comments, attachments, assignment (`_assign`) | ✅ | standard Frappe (`frappe.client`, ToDo, File) |
| Timesheets (actuals) | ✅ | `/api/resource/Timesheet` (standard ERPNext) |

**Use custom `pulse.api.*` endpoints** only where generic REST would be chatty or cannot express the transaction:

| Need | Why custom | Endpoint |
|---|---|---|
| Board view (columns + cards) | one lean call vs many | `pulse.api.board.get_board` |
| Move a card (state + rank + status log) | atomic multi-write | `pulse.api.board.move_card` |
| Backlog view / reorder | ordered lean payload | `pulse.api.backlog.get_backlog`, `reorder_backlog` |
| Sprint lifecycle | multi-step transactions | `pulse.api.sprint.*` |
| Quick-add card | one-call ergonomics | `pulse.api.task.quick_create_task` |
| Metrics for SPA | shaped time-series | `pulse.api.metrics.get_burndown`, `get_velocity` |
| App settings for SPA | single bootstrap call | `pulse.api.settings.get_settings` |

---

## 4. Endpoint Reference

All custom endpoints are `@frappe.whitelist()`. All enforce `frappe.has_permission` (or route through the document API, which enforces it). Method is `POST` for any state change; read-only endpoints accept `GET`. Standard envelope: Frappe wraps the return value as `{"message": <payload>}`.

---

### 4.1 Board

#### `pulse.api.board.get_board`
- **Method / path:** `GET /api/method/pulse.api.board.get_board`
- **Purpose:** Return the board for a project/sprint as columns (workflow states) each holding an ordered, **lean** list of cards.
- **Params:** `project` (str, reqd) · `sprint` (str, optional; defaults to active sprint) · `assignee` (str, optional filter) · `task_type` (str, optional).
- **Permission behavior:** requires read permission on the Project; card list built via `frappe.get_list("Task", ...)` which auto-applies Task DocPerm + User Permissions. No `ignore_permissions`.
- **Response schema:**
  ```json
  {
    "message": {
      "project": "PROJ-0001",
      "sprint": "SPR-PROJ-0001-0007",
      "columns": [
        {
          "state": "In Progress",
          "wip_limit": 5,
          "cards": [
            {
              "name": "TASK-0042",
              "subject": "Login page",
              "workflow_state": "In Progress",
              "pulse_story_points": 3,
              "pulse_rank": 100,
              "task_type": "Story",
              "assignees": ["dev@x.com"],
              "exp_end_date": "2026-07-10"
            }
          ]
        }
      ]
    }
  }
  ```
- **Example (curl):**
  ```bash
  curl -G 'https://site/api/method/pulse.api.board.get_board' \
       --data-urlencode 'project=PROJ-0001' \
       -H 'Authorization: token KEY:SECRET'
  ```
- **Example (frappe.call):**
  ```js
  frappe.call({ method: "pulse.api.board.get_board",
                args: { project: "PROJ-0001" } })
        .then(r => renderBoard(r.message));
  ```

#### `pulse.api.board.move_card`
- **Method / path:** `POST /api/method/pulse.api.board.move_card`
- **Purpose:** Move a card to a new column (workflow state) and/or reposition it; persists rank and lets the Status Log doc-event fire.
- **Params:** `task` (str, reqd) · `to_state` (str, reqd) · `new_rank` (int, optional) · `sprint` (str, optional).
- **Permission behavior:** `frappe.has_permission("Task", "write", doc=task)` enforced; the state change goes through the document API / workflow `apply_workflow`, so the workflow transition's role gating **and** the Status Log `on_update` doc-event both run. Rank saved on the same doc. No permission bypass.
- **Response schema:**
  ```json
  { "message": { "name": "TASK-0042", "workflow_state": "Done",
                 "pulse_rank": 120, "status": "Completed" } }
  ```
- **Example (frappe.call):**
  ```js
  frappe.call({ method: "pulse.api.board.move_card",
    args: { task: "TASK-0042", to_state: "Done", new_rank: 120 } });
  ```

---

### 4.2 Backlog

#### `pulse.api.backlog.get_backlog`
- **Method / path:** `GET /api/method/pulse.api.backlog.get_backlog`
- **Purpose:** Ordered backlog (tasks not yet in an active sprint, or all sprintless tasks) for planning; lean payload, paginated.
- **Params:** `project` (str, reqd) · `include_sprint` (bool, default false) · `start` (int, default 0) · `page_length` (int, default 50).
- **Permission behavior:** `get_list` on Task → DocPerm/User Permission applied automatically.
- **Response schema:**
  ```json
  { "message": {
      "total": 213,
      "start": 0,
      "page_length": 50,
      "items": [
        { "name": "TASK-0101", "subject": "Refactor auth",
          "pulse_story_points": 5, "pulse_rank": 10,
          "task_type": "Story", "pulse_epic": "TASK-0009" }
      ] } }
  ```
- **Example (curl):**
  ```bash
  curl -G 'https://site/api/method/pulse.api.backlog.get_backlog' \
       --data-urlencode 'project=PROJ-0001' --data-urlencode 'page_length=50' \
       -H 'Authorization: token KEY:SECRET'
  ```

#### `pulse.api.backlog.reorder_backlog`
- **Method / path:** `POST /api/method/pulse.api.backlog.reorder_backlog`
- **Purpose:** Persist new backlog ordering after drag-and-drop by writing `pulse_rank` on affected tasks.
- **Params:** `project` (str, reqd) · `ordered` (JSON array of `{task, rank}`, reqd).
- **Permission behavior:** each task updated via document API with `has_permission("Task","write")`; a task the user cannot write raises `PermissionError` and the batch is rolled back (transaction). No bypass.
- **Response schema:** `{ "message": { "updated": 12 } }`
- **Example (frappe.call):**
  ```js
  frappe.call({ method: "pulse.api.backlog.reorder_backlog",
    args: { project: "PROJ-0001",
            ordered: [{task:"TASK-0101",rank:10},{task:"TASK-0102",rank:20}] } });
  ```

---

### 4.3 Sprint

#### `pulse.api.sprint.create_sprint`
- **Method / path:** `POST /api/method/pulse.api.sprint.create_sprint`
- **Purpose:** Create a Planned sprint for a project.
- **Params:** `project` (str, reqd) · `sprint_name` (str, reqd) · `start_date` (date) · `end_date` (date) · `goal` (str, optional).
- **Permission behavior:** `frappe.get_doc({...}).insert()` → create permission on `Pulse Sprint` enforced by the framework.
- **Response schema:** `{ "message": { "name": "SPR-PROJ-0001-0008", "status": "Planned" } }`
- **Example (curl):**
  ```bash
  curl -X POST 'https://site/api/method/pulse.api.sprint.create_sprint' \
       -H 'Authorization: token KEY:SECRET' \
       -H 'Content-Type: application/json' \
       -d '{"project":"PROJ-0001","sprint_name":"Sprint 8","start_date":"2026-07-07","end_date":"2026-07-20"}'
  ```

#### `pulse.api.sprint.start_sprint`
- **Method / path:** `POST /api/method/pulse.api.sprint.start_sprint`
- **Purpose:** Transition a Planned sprint to Active; sets `is_active`, snapshots `planned_points`, enforces one Active sprint per project.
- **Params:** `sprint` (str, reqd).
- **Permission behavior:** write permission on the Sprint; single-active-sprint rule enforced in the doctype `validate` (not the endpoint), so it holds regardless of entry path.
- **Response schema:** `{ "message": { "name": "SPR-PROJ-0001-0008", "status": "Active", "planned_points": 34 } }`

#### `pulse.api.sprint.close_sprint`
- **Method / path:** `POST /api/method/pulse.api.sprint.close_sprint`
- **Purpose:** Complete a sprint; compute `completed_points`/`velocity`, and (per `carry_over`) move spillover tasks to a target sprint or back to backlog.
- **Params:** `sprint` (str, reqd) · `carry_over_to` (str, optional target sprint) · `carry_over` (bool, default true).
- **Permission behavior:** write permission on the Sprint; each carried-over task moved via document API (Task write permission enforced per task).
- **Response schema:**
  ```json
  { "message": { "name": "SPR-PROJ-0001-0008", "status": "Completed",
                 "completed_points": 29, "velocity": 29,
                 "spillover": 2, "carried_to": "SPR-PROJ-0001-0009" } }
  ```

#### `pulse.api.sprint.get_active_sprint`
- **Method / path:** `GET /api/method/pulse.api.sprint.get_active_sprint`
- **Purpose:** Return the current Active sprint for a project (used to bootstrap board/burndown).
- **Params:** `project` (str, reqd).
- **Permission behavior:** read permission on Sprint/Project.
- **Response schema:**
  ```json
  { "message": { "name": "SPR-PROJ-0001-0007", "sprint_name": "Sprint 7",
                 "start_date": "2026-06-23", "end_date": "2026-07-06",
                 "planned_points": 34, "completed_points": 12 } }
  ```
- **Example (frappe.call):**
  ```js
  frappe.call({ method: "pulse.api.sprint.get_active_sprint",
                args: { project: "PROJ-0001" } });
  ```

---

### 4.4 Task

#### `pulse.api.task.quick_create_task`
- **Method / path:** `POST /api/method/pulse.api.task.quick_create_task`
- **Purpose:** One-call card creation from the board/backlog quick-add (subject + minimal agile fields).
- **Params:** `project` (str, reqd) · `subject` (str, reqd) · `task_type` (str, optional) · `pulse_story_points` (float, optional) · `pulse_sprint` (str, optional) · `pulse_epic` (str, optional) · `assignee` (str, optional).
- **Permission behavior:** `frappe.get_doc({"doctype":"Task",...}).insert()` → Task create permission enforced. If `assignee` given, assignment goes through standard `add_assignment`, which triggers the **hierarchical-rank check** (Canonical §6) — assigning to a senior beyond your rank raises `ValidationError`. No `ignore_permissions`.
- **Response schema:**
  ```json
  { "message": { "name": "TASK-0333", "subject": "Fix pagination",
                 "workflow_state": "Backlog", "project": "PROJ-0001" } }
  ```
- **Example (curl):**
  ```bash
  curl -X POST 'https://site/api/method/pulse.api.task.quick_create_task' \
       -H 'Authorization: token KEY:SECRET' -H 'Content-Type: application/json' \
       -d '{"project":"PROJ-0001","subject":"Fix pagination","task_type":"Bug","pulse_story_points":2}'
  ```

---

### 4.5 Metrics

Read-only, shaped time-series for SPA charts. These wrap the same Script Reports documented in Document 11; they never accept or compute actuals from the client.

#### `pulse.api.metrics.get_burndown`
- **Method / path:** `GET /api/method/pulse.api.metrics.get_burndown`
- **Purpose:** Per-day ideal vs actual remaining points for a sprint (SPA burndown chart).
- **Params:** `sprint` (str, reqd).
- **Permission behavior:** read permission on the Sprint/Project; data drawn from Status Log with standard permission filtering.
- **Response schema:**
  ```json
  { "message": {
      "sprint": "SPR-PROJ-0001-0007",
      "committed": 34,
      "series": [
        {"date":"2026-06-23","ideal":34,"actual":34},
        {"date":"2026-06-24","ideal":30.6,"actual":31}
      ] } }
  ```
- **Example (frappe.call):**
  ```js
  frappe.call({ method: "pulse.api.metrics.get_burndown",
                args: { sprint: "SPR-PROJ-0001-0007" } });
  ```

#### `pulse.api.metrics.get_velocity`
- **Method / path:** `GET /api/method/pulse.api.metrics.get_velocity`
- **Purpose:** Completed points per recent sprint (SPA velocity chart + forecast).
- **Params:** `project` (str, reqd) · `last_n` (int, default 6).
- **Permission behavior:** read permission on Project; reads computed Sprint fields.
- **Response schema:**
  ```json
  { "message": {
      "average": 27.5,
      "series": [
        {"sprint":"Sprint 6","planned":30,"completed":28},
        {"sprint":"Sprint 7","planned":34,"completed":27}
      ] } }
  ```

---

### 4.6 Settings

#### `pulse.api.settings.get_settings`
- **Method / path:** `GET /api/method/pulse.api.settings.get_settings`
- **Purpose:** Single bootstrap call returning app config the SPA needs (default sprint length, board type, notification toggles, workflow states for board columns). Read-only projection of the **Pulse Settings** single doctype — it does **not** return the role-rank map to non-privileged users.
- **Params:** none.
- **Permission behavior:** read permission on `Pulse Settings`; sensitive fields (role ranks) filtered unless the user is `Pulse Admin`/`System Manager`.
- **Response schema:**
  ```json
  { "message": {
      "default_sprint_length_days": 14,
      "default_board_type": "Scrum",
      "email_notifications": 1,
      "desktop_notifications": 1,
      "workflow_states": ["Backlog","To Do","In Progress","In Review","Done"] } }
  ```
- **Example (frappe.call):**
  ```js
  frappe.call({ method: "pulse.api.settings.get_settings" })
        .then(r => bootPulse(r.message));
  ```

*(Settings writes use the standard document API on the Pulse Settings single — `PUT /api/resource/Pulse Settings/Pulse Settings` — gated to `Pulse Admin`/`System Manager` by DocPerm. No custom write endpoint.)*

---

## 5. Error Handling & Status Codes

Pulse relies on Frappe's standard exception → HTTP mapping; endpoints raise, they do not invent envelopes.

| Situation | Raise | HTTP |
|---|---|---|
| Success | return value | `200` |
| Not authenticated | (framework) | `401` |
| No permission on doc/doctype | `frappe.PermissionError` | `403` |
| Missing/invalid argument | `frappe.ValidationError` | `417` (Frappe) |
| Business rule (e.g. 2nd active sprint, assign-up violation) | `frappe.ValidationError` | `417` |
| Document not found | `frappe.DoesNotExistError` | `404` |
| Duplicate | `frappe.DuplicateEntryError` | `409` |
| Server error | `Exception` | `500` |

Error body follows Frappe's shape (`exc_type`, `_server_messages`, traceback in developer mode only). The SPA surfaces `_server_messages` to the user. Validation and permission failures are **never** swallowed or downgraded to a `200`.

---

## 6. Pagination

- **Generic REST:** `limit_start` + `limit_page_length` (default page length applies; pass `limit_page_length=0` only for trusted, bounded reads).
- **Custom list endpoints** (`get_backlog`, and board columns when very large): accept `start` + `page_length`, return `total`/`start`/`page_length` alongside `items`. Board columns are capped and lazy-load additional cards on scroll to keep the payload lean (Analysis §362, §369).
- Ordering for paginated agile lists is by `pulse_rank` (indexed), so paging is stable across requests.

---

## 7. Rate / Performance Notes

- **Lean payloads:** board/backlog return only card-face fields via `get_list` field pruning — never full documents (Analysis §210, §369).
- **Indexes:** hot columns are indexed — Task `project`, `workflow_state`, `pulse_sprint`, `pulse_rank`; Status Log `task`, `sprint`, `changed_on` (Canonical §3.2, Analysis §337). Board/metric queries stay index-served.
- **Precomputed metrics:** burndown/velocity read cached snapshots produced by the daily scheduler (Document 11 §7), so chart endpoints do not re-scan the full Status Log per request (Analysis §363, §373).
- **Optimistic UI + debounced writes:** the SPA applies moves optimistically and debounces `move_card`/`reorder_backlog` persistence to avoid write storms during drag (Analysis §371).
- **Rate limiting:** reuse Frappe's built-in rate limiting / `frappe.rate_limiter` on write endpoints if abuse is observed; no custom throttler.
- **No N+1:** batch reads (`get_list` with all needed fields) rather than per-card fetches; assignment (`_assign`) resolved in the same query.

---

*End of Document 14 of 21.*
