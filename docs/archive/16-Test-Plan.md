# Pulse — Test Plan

**Document 16 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26 · App `pulse` · Module `Pulse`
**Governing rule:** Test the *extensions*, not the framework. Trust Frappe for CRUD/permission internals; verify Pulse logic and its integration with core Task/Project.

---

## 1. Test strategy

Pulse is a thin agile layer over ERPNext core. The testing philosophy (analysis §20, §23) is:

- **Do not re-test the framework.** Frappe already tests document CRUD, permissions, workflow engine, assignment, notifications. Pulse tests the *new logic* and the *seams* where Pulse meets core.
- **High-value targets:** the status-log writer, the hierarchical-assignment rule, velocity/burndown math, and the one-active-sprint constraint — these are the four bespoke pieces of business logic.
- **Guard the reuse contract:** integration tests must prove that a Pulse Task rolls up to Project costing, that Timesheet hours become actuals, and that workflow transitions behave.
- **Guard security:** permission tests must prove no blanket `ignore_permissions` regression and that `permlevel` protects financial fields.
- **Guard migration:** migrating old `Pulse *` data → core must be correct and idempotent.
- **Guard the UI:** board drag and sprint close must work end-to-end (Phase 2 SPA).

**Coverage philosophy:** aim for near-100% branch coverage on the four bespoke logic modules; broad-but-shallow coverage on glue; e2e only for the highest-visibility flows.

---

## 2. Test levels

| Level | Framework | What it covers | Phase |
|---|---|---|---|
| **Unit** | `FrappeTestCase` (pytest-style) | Status-log writer, hierarchy rule, velocity/burndown calc, one-active-sprint validate | P1 |
| **Integration** | `FrappeTestCase` (with real Task/Project/Timesheet) | Task→Project costing rollup, Timesheet actuals, workflow transitions | P1 |
| **Permission** | `FrappeTestCase` with `frappe.set_user()` | Assign-down enforcement, `permlevel` on financial fields, no-bypass | P1 |
| **Migration** | `FrappeTestCase` seeding legacy rows | Old `Pulse *` → core Task/Project; idempotency | P1 |
| **UI / e2e** | Cypress (Frappe convention) / Playwright | Board drag persists state+rank+log; sprint plan→active→close | P2 |

---

## 3. Unit tests (Pulse bespoke logic)

### 3.1 Status-log writer

Verifies the `on_update` doc-event appends a **Pulse Task Status Log** row on `workflow_state`/`status` change, with correct `from_state`, `to_state`, `changed_by`, `changed_on`, and `points_at_change` (story-points snapshot). Must NOT log when state is unchanged; must be append-only (no user edit/delete).

```python
# pulse/pulse/doctype/pulse_task_status_log/test_pulse_task_status_log.py
import frappe
from frappe.tests.utils import FrappeTestCase

class TestStatusLogWriter(FrappeTestCase):
    def setUp(self):
        self.project = make_test_project(enable_scrum=1)
        self.task = make_test_task(self.project, story_points=5, workflow_state="To Do")

    def test_logs_on_state_change(self):
        self.task.workflow_state = "In Progress"
        self.task.save()
        logs = frappe.get_all(
            "Pulse Task Status Log",
            filters={"task": self.task.name},
            fields=["from_state", "to_state", "points_at_change"],
            order_by="changed_on desc",
        )
        self.assertEqual(logs[0].from_state, "To Do")
        self.assertEqual(logs[0].to_state, "In Progress")
        self.assertEqual(logs[0].points_at_change, 5)

    def test_no_log_when_state_unchanged(self):
        before = frappe.db.count("Pulse Task Status Log", {"task": self.task.name})
        self.task.pulse_story_points = 8   # non-state field
        self.task.save()
        after = frappe.db.count("Pulse Task Status Log", {"task": self.task.name})
        self.assertEqual(before, after)

    def test_log_is_append_only(self):
        self.task.workflow_state = "In Progress"
        self.task.save()
        log = frappe.get_last_doc("Pulse Task Status Log", filters={"task": self.task.name})
        log.to_state = "Done"
        self.assertRaises(frappe.PermissionError, log.save)  # read-only / permlevel
```

### 3.2 Hierarchical assignment rule

A user may assign work only to users whose **max rank ≤ their own** (assign down/sideways, never up), driven by Pulse Role Rank in Pulse Settings (canonical §6).

```python
# pulse/tests/test_hierarchy_assignment.py
class TestHierarchyAssignment(FrappeTestCase):
    def setUp(self):
        self.manager = make_user_with_role("Pulse Manager")        # rank 80
        self.junior  = make_user_with_role("Pulse Junior Developer")# rank 20
        self.task = make_test_task(make_test_project())

    def test_senior_can_assign_down(self):
        frappe.set_user(self.manager)
        assign_task(self.task, self.junior)      # should succeed
        self.assertIn(self.junior, get_assignees(self.task))

    def test_junior_cannot_assign_up(self):
        frappe.set_user(self.junior)
        self.assertRaises(frappe.ValidationError, assign_task, self.task, self.manager)

    def test_sideways_allowed(self):
        peer = make_user_with_role("Pulse Junior Developer")
        frappe.set_user(self.junior)
        assign_task(self.task, peer)             # equal rank -> allowed
        self.assertIn(peer, get_assignees(self.task))
```

### 3.3 Velocity / burndown calc

Velocity = completed points per sprint (from Status Log at close). Burndown = remaining points per working day (Status Log + sprint dates + Holiday List working days). Pure functions, tested with fixed inputs.

```python
# pulse/tests/test_metrics.py
class TestVelocityBurndown(FrappeTestCase):
    def test_velocity_sums_completed_points(self):
        sprint = make_sprint(status="Completed")
        complete_task(sprint, points=5)
        complete_task(sprint, points=3)
        add_task(sprint, points=8, state="In Progress")  # not done
        self.assertEqual(compute_velocity(sprint.name), 8)

    def test_burndown_ideal_and_actual(self):
        sprint = make_sprint(start="2026-07-06", end="2026-07-17", planned_points=10)
        series = compute_burndown(sprint.name)
        self.assertEqual(series[0].remaining, 10)         # day 0
        self.assertEqual(series[-1].ideal, 0)             # ideal ends at 0
        # weekends excluded when Holiday List set
        self.assertNotIn("2026-07-11", [d.date for d in series])  # Saturday
```

### 3.4 One-active-sprint rule

Only one **Active** sprint per project (canonical §3.1).

```python
# pulse/pulse/doctype/pulse_sprint/test_pulse_sprint.py
class TestOneActiveSprint(FrappeTestCase):
    def test_second_active_sprint_rejected(self):
        p = make_test_project()
        make_sprint(project=p, status="Active")
        with self.assertRaises(frappe.ValidationError):
            make_sprint(project=p, status="Active")

    def test_active_allowed_in_other_project(self):
        make_sprint(project=make_test_project(), status="Active")
        make_sprint(project=make_test_project(), status="Active")  # ok

    def test_closing_frees_the_slot(self):
        p = make_test_project()
        s1 = make_sprint(project=p, status="Active")
        s1.status = "Completed"; s1.save()
        make_sprint(project=p, status="Active")  # now allowed
```

---

## 4. Integration tests (Pulse ↔ ERPNext core)

### 4.1 Task → Project costing rollup

Proves a Pulse Task is a real Task and contributes to Project costing.

```python
class TestCostingRollup(FrappeTestCase):
    def test_task_rolls_up_to_project(self):
        project = make_test_project()
        task = make_test_task(project, story_points=5)
        make_timesheet(task, hours=4, activity_type="Development")
        project.reload()
        self.assertGreater(project.total_costing_amount, 0)
```

### 4.2 Timesheet actuals

Actual effort = Timesheet hours; never hand-entered (canonical §2).

```python
class TestTimesheetActuals(FrappeTestCase):
    def test_actual_hours_from_timesheet(self):
        task = make_test_task(make_test_project())
        make_timesheet(task, hours=3)
        make_timesheet(task, hours=2)
        self.assertEqual(actual_hours_for_task(task.name), 5)
```

### 4.3 Workflow transitions

`Backlog → To Do → In Progress → In Review → Done`; `Done` sets Task `status=Completed` so core closure/costing works.

```python
class TestWorkflowTransitions(FrappeTestCase):
    def test_done_marks_task_completed(self):
        task = make_test_task(make_test_project(), workflow_state="In Review")
        apply_workflow(task, "Done")
        task.reload()
        self.assertEqual(task.status, "Completed")

    def test_illegal_transition_blocked(self):
        task = make_test_task(make_test_project(), workflow_state="Backlog")
        self.assertRaises(frappe.ValidationError, apply_workflow, task, "Done")
```

---

## 5. Permission tests

```python
class TestPermissions(FrappeTestCase):
    def test_viewer_cannot_edit_financial_fields(self):
        viewer = make_user_with_role("Pulse Viewer")
        task = make_test_task(make_test_project())
        frappe.set_user(viewer)
        task.reload()
        task.some_permlevel1_costing_field = 999
        self.assertRaises(frappe.PermissionError, task.save)

    def test_writes_go_through_permissions(self):
        # regression guard: no blanket ignore_permissions in API
        viewer = make_user_with_role("Pulse Viewer")
        frappe.set_user(viewer)
        self.assertRaises(frappe.PermissionError,
                          frappe.get_doc({"doctype": "Pulse Sprint",
                                          "sprint_name": "X", "project": "P"}).insert)

    def test_permission_query_scopes_projects(self):
        # user restricted to Project A cannot see Tasks of Project B
        ...
```

Checklist:
- Assign-down enforced (covered in §3.2, re-asserted at API layer).
- `permlevel` guards financial fields on Task/Project (delivery users read-only).
- No endpoint bypasses permissions (`ignore_permissions=True` search must return zero hits in `pulse/api`).
- `permission_query_conditions` scopes lists to accessible projects.

---

## 6. Migration tests

```python
class TestLegacyMigration(FrappeTestCase):
    def setUp(self):
        self.legacy_project = make_legacy_pulse_project()
        self.legacy_task = make_legacy_pulse_task(self.legacy_project, story_points=5)

    def test_pulse_task_becomes_core_task(self):
        run_migration()
        core = frappe.get_doc("Task", {"pulse_legacy_ref": self.legacy_task.name})
        self.assertEqual(core.pulse_story_points, 5)

    def test_migration_is_idempotent(self):
        run_migration()
        count1 = frappe.db.count("Task")
        run_migration()                      # re-run
        self.assertEqual(count1, frappe.db.count("Task"))

    def test_costing_intact_after_migration(self):
        run_migration()
        project = frappe.get_doc("Project", {"pulse_legacy_ref": self.legacy_project.name})
        self.assertIsNotNone(project.total_costing_amount)
```

---

## 7. UI / e2e tests (Phase 2)

Cypress (Frappe convention; Playwright acceptable). Covers the two highest-visibility flows.

- **Board drag:** drag a card `To Do → In Progress`; assert (a) card in new column after reload, (b) `workflow_state` updated, (c) a Status Log row created, (d) `pulse_rank` persisted on reorder, (e) optimistic UI reconciles with server.
- **Sprint close:** plan a sprint, activate it, complete tasks, close it; assert velocity recorded, burndown final point = 0/remaining, spillover moved to backlog/next sprint.

```javascript
// pulse/cypress/integration/board_drag.spec.js
describe("Pulse board drag", () => {
  it("moves a card and logs the transition", () => {
    cy.login(); cy.visit("/pulse/board/PROJ-001");
    cy.get('[data-card="TASK-001"]').drag('[data-column="In Progress"]');
    cy.reload();
    cy.get('[data-column="In Progress"]').should("contain", "TASK-001");
    cy.request("/api/method/pulse.api.board.status_log?task=TASK-001")
      .its("body.message.0.to_state").should("eq", "In Progress");
  });
});
```

---

## 8. Test data / fixtures

- **Factory helpers** in `pulse/tests/utils.py`: `make_test_project`, `make_test_task`, `make_sprint`, `make_user_with_role`, `make_timesheet`, `make_legacy_pulse_project/task`. Each creates the minimal valid core doc + Pulse fields.
- **Deterministic masters:** a test Company, Activity Type ("Development" with costing/billing rates), a Holiday List (weekends) for burndown working-day tests.
- **Role/rank seed:** ensure Pulse Settings has default Role Ranks before hierarchy tests (setUp loads the fixture or inserts ranks).
- **Isolation:** `FrappeTestCase` wraps each test in a transaction and rolls back; avoid committing. Use `frappe.set_user()` / `frappe.set_user("Administrator")` in setUp/tearDown.

---

## 9. Frappe test framework usage

- Base class **`frappe.tests.utils.FrappeTestCase`** (auto transaction rollback, helpers).
- File naming: `test_<doctype>.py` beside each doctype; cross-cutting suites under `pulse/tests/`.
- Run: `bench --site <site> run-tests --app pulse` (all) or `--module pulse.tests.test_metrics` (targeted); `--doctype "Pulse Sprint"` for a single doctype.
- Use `frappe.get_doc(...).insert()` / `.save()` so validations and doc-events fire (this is deliberate — we test the seam).
- Use `self.assertDocumentEqual`, `frappe.set_user`, `frappe.db.rollback` as needed.

---

## 10. CI setup

GitHub Actions workflow `.github/workflows/ci.yml`:

1. **Matrix:** target Frappe v16 / ERPNext v16 (add next-version job for early-warning against upgrades).
2. **Services:** MariaDB, Redis.
3. **Steps:** `bench init` → `bench get-app erpnext` → `bench get-app pulse` → create site → `bench install-app pulse` → `bench migrate`.
4. **Lint:** `ruff check` (Python) + `prettier --check` (JS/Vue) — see Coding Standards (Doc 19).
5. **Tests:** `bench --site ci run-tests --app pulse --coverage`.
6. **e2e (Phase 2):** Cypress headless run.
7. **Gate:** merge blocked unless install + migrate + lint + unit/integration/permission tests pass; PR checklist enforces the reuse gate (Doc 19).

---

## 11. Coverage targets

| Area | Target |
|---|---|
| Status-log writer | ~100% branch |
| Hierarchy assignment rule | ~100% branch |
| Velocity/burndown/burnup calc | ~100% branch |
| One-active-sprint validate | ~100% branch |
| Sprint/Settings/Role Rank controllers | ≥ 90% line |
| API endpoints (thin) | ≥ 80% line |
| Migration script | ≥ 90% line (happy path + idempotency + rollback trigger) |
| Overall app | ≥ 80% line |

Framework code (Frappe/ERPNext) is explicitly out of scope for coverage.

---

## 12. Acceptance test matrix (mapped to functional requirements)

| ID | Functional requirement (source) | Test(s) | Level |
|---|---|---|---|
| AT-01 | O1: plan & run a sprint on core Task data | §3.4, §4.3, §7 sprint close | Unit/Int/e2e |
| AT-02 | O2: board ≤2 clicks, <1s / 500 tasks | §7 board drag + perf assertion | e2e/perf |
| AT-03 | O3: 100% financial integration preserved | §4.1, §4.2 | Integration |
| AT-04 | O4: ≥70% reuse (thin logic only) | Coverage scoped to bespoke modules (§11) | Meta |
| AT-05 | O5: hierarchical assignment (down only) | §3.2, §5 | Unit/Perm |
| AT-06 | O6: upgrade-safe (no core edits) | CI install/migrate on clean bench (§10) | CI |
| AT-07 | Canonical §3.1: one Active sprint/project | §3.4 | Unit |
| AT-08 | Canonical §3.2: status log append-only | §3.1 | Unit |
| AT-09 | Canonical §5: `Done` → Task `status=Completed` | §4.3 | Integration |
| AT-10 | Canonical §8: velocity + burndown correct | §3.3 | Unit |
| AT-11 | Security §24: no permission bypass; permlevel | §5 | Permission |
| AT-12 | §7 (Doc 15 M0): migration correct + idempotent | §6 | Migration |

*End of Document 16.*
