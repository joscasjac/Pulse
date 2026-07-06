# Pulse — Business Requirements

**Document 3 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26
**Governing rule:** Reuse ERPNext → Extend ERPNext → Build new (only if no equivalent).

---

## 1. Business Objectives & Drivers

| # | Objective | Driver | Success measure |
|---|---|---|---|
| BO1 | Reduce tool sprawl and subscription cost | ERPNext shops pay separately for Jira/Plane | Retire external agile-tool subscription for adopting teams |
| BO2 | Increase billable accuracy | Delivery in external tools never reaches ERPNext costing/billing | Timesheet completeness ↑; project margin visibility ↑ |
| BO3 | Improve data quality upstream of finance | Teams working "around" ERPNext degrade its data | More delivery activity captured natively in ERPNext |
| BO4 | Give delivery teams a modern experience inside ERPNext | Dated ERPNext PM UX pushes teams away | Adoption by delivery teams; ≤ 2-click common actions |
| BO5 | Preserve the ERP financial moat | Financial integration is the differentiator Jira/Plane lack | 100% of Pulse tasks roll up to Project costing/billing |
| BO6 | Minimize total cost of ownership | Custom code is a maintenance liability | ≥ 70% reuse/extension; upgrade-safe; zero core edits |
| BO7 | Community leadership | Become the reference agile-PM app for Frappe (like HRMS for HR) | OSS adoption; contributor base |

**Strategic thesis:** ERPNext is the **system of record** (costing, billing, timesheets, margin); Pulse is the **system of engagement** (sprints, boards, roadmap, modern UI). One data model, two experiences — no fork.

---

## 2. As-Is vs To-Be Processes

### 2.1 Project delivery
| | As-Is | To-Be (Pulse) |
|---|---|---|
| Where work is planned | Jira/Plane (external) or ERPNext Task list (dated) | Pulse Sprint + Backlog on core Tasks |
| Work item | Jira issue / Plane issue (separate system) OR ERPNext Task with no agile fields | ERPNext **Task** + `pulse_*` fields (card = Task) |
| Board | External tool, or basic Frappe Kanban | Sprint-scoped board; columns = Pulse Task Workflow states |
| Agile metrics | External tool only | Velocity/Burndown from Pulse Task Status Log, in ERPNext |
| Finance linkage | Manual/none; re-keying | Automatic — cards are Tasks under a Project |

### 2.2 Time capture → billing
| | As-Is | To-Be (Pulse) |
|---|---|---|
| Where time is logged | External tracker, then re-entered; or ad hoc | ERPNext **Timesheet / Timesheet Detail** |
| Actual effort on card | Hand-entered, drifts from reality | Derived from Timesheet — never hand-entered |
| Rates | Disconnected | **Activity Type / Activity Cost** (billing & costing) |
| Roll-up to margin/invoice | Manual reconciliation | Automatic to Project costing/billing |

### 2.3 Assignment
| | As-Is | To-Be (Pulse) |
|---|---|---|
| Mechanism | Ad hoc; external tool assignees | Frappe `_assign` / ToDo (reuse) |
| Hierarchy control | None or manual convention | Server-side assign-down/sideways rule via role ranks |
| Enforcement | UI convention only | `validate`/assignment hook, never UI-only |

---

## 3. Business Rules

| # | Rule | Enforcement |
|---|---|---|
| BR1 | A Pulse card **is** an ERPNext Task; a Pulse project **is** an ERPNext Project. No parallel work-item table. | Architecture / Reuse Matrix gate |
| BR2 | **One Active sprint per project** at any time. | `validate` on Pulse Sprint (`is_active`) |
| BR3 | **Assign-down/sideways only** — a user may assign only to users whose max role rank ≤ their own. | `validate`/assignment hook using Pulse Role Rank map |
| BR4 | Estimation is in **story points** (`pulse_story_points`); relative, not hours. | Field on Task; used by velocity/burndown |
| BR5 | **Actuals come from Timesheet**, never hand-entered on the card. | No actual-hours field; reuse Timesheet |
| BR6 | Agile is **opt-in per project** (`pulse_enable_scrum`). | Field on Project; gates views/fields |
| BR7 | Board columns/statuses come from **Frappe Workflow**, not a custom status field. | Pulse Task Workflow; `workflow_state` |
| BR8 | Reaching **Done** sets Task `status = Completed` so core costing/closure works. | Workflow field mapping / doc-event |
| BR9 | **Status Log is append-only** — never edited/deleted by users. | permlevel / read-only perms |
| BR10 | **Financial fields protected** so delivery users cannot edit costing/billing. | `permlevel` on Task/Project financial fields |
| BR11 | No blanket permission bypass in APIs. | No `ignore_permissions=True`; `frappe.has_permission` per endpoint |
| BR12 | Backlog order is an attribute (`pulse_rank`, lower = higher), not a separate table. | Field on Task |
| BR13 | Velocity = completed points at sprint close; captured on the sprint. | Computed, read-only on Pulse Sprint |

---

## 4. ROI / Cost Justification

### 4.1 Direct subscription savings
- Replacing a **Jira** or **Plane** subscription for teams already licensed for ERPNext removes a recurring per-user SaaS cost. For a 25-person delivery org, external agile tooling is a material annual line item that Pulse can retire once adoption reaches parity on core flows.

### 4.2 Billable accuracy uplift
- Today, delivery time logged in an external tool is re-keyed (or lost) before it reaches billing. Pulse routes time through **Timesheet → Activity Cost → Project costing/billing**, so:
  - Fewer un-billed hours (leakage) — every logged card-hour is a billable/costed line.
  - Faster, more accurate invoicing (no reconciliation between two systems).
  - Real-time **margin visibility** per project because effort and cost live where the accounting is.

### 4.3 Reduced build & maintenance cost
- The reuse-first architecture delivers **≥ 70% of features via reuse/extension**, so Pulse ships and is maintained with a fraction of the custom code a parallel system would need. Framework provides permissions, assignment, notifications, API, audit — for free. Upgrade-safety (fixtures, no core edits) avoids costly re-work on each ERPNext upgrade.

### 4.4 Cost avoidance vs. the deprecated build
- The earlier parallel-doctype build carried an install crash, a missing flagship page, broken sync, a destructive nightly job, and systemic permission bypass. Re-baselining on core eliminates most of that defect surface **by construction**, avoiding the ongoing cost of hand-maintaining duplicate plumbing.

**Net ROI drivers:** (subscription retired) + (recovered billable hours) + (lower dev/maintenance cost) − (one-time migration + adoption effort).

---

## 5. Stakeholder Needs Matrix

| Stakeholder | Needs | How Pulse meets it |
|---|---|---|
| **Pulse Admin** | Clean install, safe upgrades, central config | Fixtures; Pulse Settings; no core edits |
| **Pulse Manager / PM** | Sprint planning, backlog, velocity/burndown, margin | Pulse Sprint, Backlog, metric reports; finance roll-up |
| **Team Lead** | Fast board, sprint scope, WIP control | Kanban board (Ph1) / SPA board (Ph2); workflow columns |
| **Senior Developer** | Estimation, sub-tasks, assign-down | Story points, `parent_task`, hierarchy rule |
| **Junior Developer / Intern** | Clear "my work"; safe surface | `_assign` views; assign-up blocked |
| **Viewer** | Read-only accurate views | Read-only role; reports/boards |
| **Finance controller** | Trusted actuals, protected financial fields | Timesheet actuals; `permlevel` protection |
| **Client stakeholder** | Confidence delivery ↔ billing align | Single source of truth; margin from real effort |
| **OSS community** | Extensible, documented, non-forking app | Stable `pulse.api.*`, hooks surface, reuse gate |

---

## 6. Compliance & Data Considerations

| Area | Consideration | Approach |
|---|---|---|
| **Access control** | Only authorized users see/edit projects, tasks, financials | Frappe RBAC (Role/DocPerm/permlevel) + **User Permission** for project/company scoping |
| **Segregation of duties** | Delivery users must not alter costing/billing | Financial fields protected via `permlevel` |
| **Auditability** | Traceable changes for delivery and finance | Frappe **Version**/Activity Timeline (reused) + append-only Pulse Task Status Log |
| **Data residency / self-host** | Enterprises need on-prem control | Standard self-hostable Frappe app; no third-party SaaS dependency |
| **Data integrity** | One source of truth, no duplication | Card = Task; links not copies; append-only history |
| **PII** | User/Employee data | Handled by Frappe framework; Pulse adds no new PII store |
| **Multi-company / multi-team** | Correct financial dimensions | Reuse Company, Cost Center, Customer, User Permissions |
| **Retention** | Historical metrics | Status Log retained for burndown/CFD/cycle-time |

---

## 7. Business Success Metrics

| Metric | Target |
|---|---|
| External agile-tool subscriptions retired (adopting teams) | Trend to 0 |
| Billable-hour leakage (logged-but-unbilled) | ↓ vs. as-is baseline |
| Project margin visibility latency | Real-time (vs. manual reconciliation) |
| Timesheet completeness for delivery teams | ↑ toward 100% |
| Delivery-team adoption (active users on Pulse boards) | Growing per release |
| Reuse ratio (features via reuse/extension) | ≥ 70% |
| Core-file edits | 0 |
| Time-to-first-sprint after install | Within one working session |
| ERPNext-upgrade break incidents | 0 (fixtures + CI) |

---

## 8. Business Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Re-cloning ERPNext (parallel doctypes) — occurred before | High | High | Reuse governance; retire `Pulse *` doctypes; Reuse Matrix (Doc 5) as gate |
| R2 | ERPNext upgrade breaks extensions | Med | High | Fixtures + custom fields + own module; CI against target versions; no core edits |
| R3 | Scope creep to full Jira parity | High | Med | MVP discipline (Doc 2 §5); phase gates |
| R4 | UX under-delivers vs. Plane | Med | High | Invest custom-code budget in front-end; frappe-ui; ≤ 2-click / < 1s targets |
| R5 | Adoption resistance (teams on Jira/Plane) | Med | High | Real parity on core flows; positioning as "not another project system" |
| R6 | Metrics need status history not natively present | High | Med | Pulse Task Status Log from day one (append-only) |
| R7 | Performance on large boards | Med | Med | Lean APIs, pagination, indexes, precomputed metrics |
| R8 | Migration cost from deprecated build's data | Med | Med | Documented one-time Pulse*→core migration (Doc 16) |
| R9 | Security regressions (permission bypass recurring) | Med | High | No blanket `ignore_permissions`; `frappe.has_permission` per endpoint; server-side hierarchy |
| R10 | Maintainer bandwidth | Med | High | Minimize code; lean on framework; tests + docs; reuse gate in PR review |

---

*End of Document 3. Proceed to Document 4 — Functional Requirements.*
