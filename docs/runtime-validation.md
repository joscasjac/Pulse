# Runtime validation evidence

## Native Task document read boundary

Reproduced private dependency title/ID disclosure through `frappe.client.get`.
Task's Frappe 16 class extension now filters dependency rows, derived dependency
IDs and an unreadable parent at `apply_fieldlevel_read_permissions`, also used
by native REST v1 document reads. The normal server-side ORM document remains
complete. A before-validation hook restores pre-existing invisible relationships
omitted by a client roundtrip; it leaves readable links editable and does not
permit new links to unreadable tasks. Administrators retain full link control.

Focused permission suite: 9 passed in 2.117s after the initial failing
reproduction. Full integration suite, with an additional mixed visible/private
removal regression: **127 passed in 19.313s**. The unit run reported 60 tests,
one skip and one error because the registry regression expected the old string
instead of the new hook list. Only that expected sequence changed; its focused
rerun passed in 0.028s, exit 0. The original full command exited 1 and is retained
as `../.work/pulse-bench/pulse-release-tests-native-reads.log`; focused logs:
`native-task-read-tests.log`, `native-task-read-tests-fixed.log`, and
`native-task-read-hook-tests.log`.

Tests invoke native client/REST document handlers against actual restricted-user
ORM permissions. They do not certify arbitrary field-list queries, exports or
every native report. Those surfaces and a live native browser read remain
separate acceptance boundaries. Deployment requires reloading the hook registry
and restarting processes to load the extended Task class.

## Release rehearsal follow-up — 2026-09-16

The current code completed `bench --site pulse-qa.localhost migrate`, including
`after_migrate` hooks. Evidence: `../.work/pulse-bench/pulse-release-migrate.log`.
This was the isolated QA site, not production.

The isolated combined CRM + ERPNext + Pulse site also passed all six CRM
integration cases in 1.068 seconds. These include permission checks, stale-edit
rejection, invalid dates and a native ERPNext Task count invariant demonstrating
that CRM completion does not create a duplicate ERPNext Task. Evidence:
`../.work/pulse-crm-qa/combined-validation.log`; setup boundaries are documented
in `crm-task-integration.md`. Browser editing and project association remain
separate outstanding acceptance items.

Read-only connected ERP email readiness is recorded in `email-reminders.md`.
An existing default outgoing account and recent sent queue entries are confirmed;
Pulse scheduler registration and actual Pulse email delivery remain unverified.

## Generic Pulse Task read scope

Complete rerun: 125 integration tests pass in 16.719s; unit run reports 59 tests,
OK with one skip in 0.090s; command exit 0. Retained log:
`../.work/pulse-bench/pulse-release-tests-read-scope.log`.

An actual restricted-user regression reproduced a cached private dependency title
and ID returned by `pulse.api.spa.get_entity`, although the task drawer already
filtered dependency targets. Generic Pulse Task serialization now filters native
dependency child rows by target read permission, rebuilds the derived ID string,
and clears an unreadable parent link in the response only. Stored links remain
untouched. Eight focused permission cases pass in 2.097s; positive readable
dependency serialization is also included in the subsequent full run.
Logs: `../.work/pulse-bench/generic-task-read-permissions.log` (reproduction) and
`generic-task-read-permissions-fixed.log`. This check covers the Pulse endpoint,
not a certification of every ERPNext/Frappe REST serialization path.

## Native dependency write permissions follow-up

Real restricted-user test reproduced a native Task Depends On write to an
unreadable target, despite Pulse's add_dependency API already rejecting it.
Task scope validation now checks read permission on newly introduced native
dependency targets. Existing links are preserved without blocking unrelated
edits when the target is no longer readable. Seven focused permission cases
pass, including denied new links and accepted visible targets.

Full backend rerun passed 124 integration tests in 17.031s; unit run reported
59 tests, OK with one skip, in 0.088s, command exit 0. Logs:
`../.work/pulse-bench/native-dependency-permissions.log` (reproduction),
`native-dependency-permissions-fixed.log`, and
`pulse-release-tests-permissions.log`. This is native write-boundary evidence;
it does not certify every generic native serialization/read surface.

## Dependency project consistency follow-up

Full-suite follow-up: 121 integration tests passed in 22.909s; unit run reported
59 tests, OK with one skip, in 0.157s. Command exited 0. Retained evidence:
`../.work/pulse-bench/pulse-release-tests-dependencies-rerun.log`.
The preceding full run failed one workload fixture because it assigned capacity
to Administrator and inherited the approved leave retained by browser QA.
The fixture now uses a unique test user; production availability logic was not
changed. The failed run remains in `pulse-release-tests-dependencies.log`.

A new real-backend regression reproduced stale Pulse Dependency source/target
project fields after a native task moved. Added a Task on_update hook to refresh
both derived fields in the same save transaction. The after_migrate path repairs
existing stale fields in batches of 500, preserves endpoints and modified dates,
and leaves orphan references intact for separate diagnosis.

All 10 focused hierarchy cases pass in 1.185s, exit 0, including relation-rich
moves (native dependencies, parent/child links, checklist and comment), direct
ERPNext task saves, late-failure rollback and twice-run migration repair.
Evidence: `../.work/pulse-bench/bulk-relations-tests-fixed.log`. The earlier
reproducing failure is retained in `bulk-relations-tests.log`. Production migration
has not run; its normal migrate/cache refresh is required to activate the hook.

Validation uses an isolated local Frappe/ERPNext site, not a production database.

- Site: `pulse-qa.localhost`.
- Frappe 16.34.0 / ERPNext 16.35.0, official `version-16` branches.
- Pulse working tree on `codex/erpnext-backlog`, base commit `96859dd` plus the backlog changes.
- Python 3.14.5; dedicated MariaDB `127.0.0.1:13316`; dedicated Redis `127.0.0.1:16316`.
- Company `Pulse QA` created through ERPNext's setup wizard functions, USD, FY2026.
- Runtime directory: `/Users/nataliayurrita/Documents/ChatGPT/Quotes/.work/pulse-bench`.

## Execution

From the runtime directory, source `runtime-env.sh`, enter `bench`, then run:

```sh
bench --site pulse-qa.localhost migrate
bench --site pulse-qa.localhost clear-cache
bench --site pulse-qa.localhost run-tests --app pulse --junit-xml-output ../pulse-tests.xml
```

The site enables `allow_tests` and the explicit `pulse_legacy_migration_tests` opt-in. The migration rehearsal refuses sites with pre-existing legacy schemas, creates historical test-only schemas, tests real SQL/ORM behavior, and removes only schemas it created. It checks source preservation, repeated migration, attachments, comments, assignments, task hierarchy, and rollback. This is a synthetic legacy-data rehearsal, not a migration of a customer's production database.

Test fixtures use unique names and transactions. Native Project membership revocation uses `Project.save()` so ERPNext also revokes its automatically created shares. Schema installation runs before tests rather than issuing committing DDL in individual test setup.

## Results

Latest combined backend validation on 2026-09-16:

- All 101 current integration tests passed in 52.227 seconds in an exclusive DB window.
- The same command ran 44 unit/unspecified-category cases; one stale fixture incorrectly omitted the original task project, simulating a project move. The fixture was corrected to represent an unchanged project. All 44 unit tests then passed together in a standalone rerun in 15.145 seconds (exit 0).
- The initial combined command therefore returned exit 1 for that fixture error; the preserved `pulse-tests.log` records this honestly. `pulse-unit-tests.log` records the passing complete unit rerun. No application code changed for this repair, and the 101 passing integration cases were not repeated.

The final expanded business suite passed all nine integration tests in 1.870 seconds (exit 0). It creates isolated real Customer Group, Customer, Item, Price List and draft Sales Order records, then verifies matching links, API/direct REST mismatch rejection, and unreadable commercial-link denial. An earlier fixture attempt imported ERPNext's global test-data bootstrap and conflicted with the QA price-list currency; those imports were removed rather than changing site defaults. Latest log: runtime `pulse-business-tests.log`.

A read-only real-backend `link_options(Project, selected="PROJ-0035")` check also retained the selected historical project outside the first 50 search results.

Subsequent focused runs after business, native-dependency analytics, and sprint hardening also passed:

- Business: 7 integration cases, 17.517 seconds (clone labels/configuration and template workload exclusion included).
- Native dependency views/analytics: 8 cases, 4.283 seconds; existing analytics integration: 2 cases, 3.967 seconds.
- Sprint lifecycle/history: 13 cases, 23.943 seconds, including a 201-task atomic closure and deleted/hidden history permissions.
- Logs: runtime `pulse-business-tests.log`, `pulse-view-dependencies-tests.log`, `pulse-analytics-tests.log`, and `pulse-sprint-tests.log`. All commands returned exit 0. Services were not restarted.

Earlier full and focused validation history:

- 71 integration tests passed in 16.189 seconds.
- 38 additional unit/unspecified-category tests passed in 0.104 seconds.
- After the Module schema migration, all four module integration tests passed; the final permission/concurrency-hardening rerun passed in 2.905 seconds, including junior visibility, many-to-many membership/progress, task project moves, and guest/date validation. Updated saved-view/preferences tests passed all three cases in 1.116 seconds. Logs: runtime `pulse-modules-tests.log` and `pulse-views-tests.log`.
- Final hierarchy hardening passed all seven bulk-hierarchy integration tests in 1.219 seconds and all four task-flexibility regressions in 0.811 seconds. Native dependency views passed all four integration cases in 1.213 seconds (direction, deduplication, visibility, and filtered endpoints). Logs: runtime `pulse-bulk-hierarchy-tests.log`, `pulse-task-flexibility-tests.log`, and `pulse-view-dependencies-tests.log`.
- Expanded scheduling passed all eight integration tests in 2.631 seconds, including atomic module membership/date changes, rollback on later validation failure, cross-project rejection, duration preservation, and project-scoped assignees. Log: runtime `pulse-scheduling-tests.log`.
- A subsequent focused real-backend task-reordering run passed all five tests in 1.541 seconds (exit 0), covering equal ranks, native status/dependency validation, rollback, and hidden-anchor denial. Log: runtime `pulse-reorder-tests.log`.
- A subsequent migration rollback error-preservation patch passed its complete seven-test unit module in 0.008 seconds. This adds one regression beyond the full-run collection; the integration suite was not repeated after that narrow exception-handling patch.

The integration run covers native workflows, task vocabulary and native dependency checks, permissions, native time and timers, synthetic legacy migration, rich task activity, intake, personal navigation, sprint history, project templates/workload, analytics, native reports, scheduled reminders, documents/collaboration transport, and saved views. Some cases deliberately mock peripheral publishing or report inputs while exercising real ORM permissions.

Earlier failing runs exposed and prompted fixes for Frappe 16 permission-hook return semantics, hook-module registry collision, native role grants, rich-document revision creation during tests, typed File migration references, and test fixture isolation. Concurrent browser Task writes triggered two native ERPNext nested-set deadlocks because the table-wide tree update touches rows beyond uniquely named fixtures. Browser writes were paused for the successful exclusive rerun; this result does not establish contention behavior under concurrent production load.

Machine-readable result: runtime `bench/pulse-tests.xml`. Full console result: runtime `pulse-tests.log`. Schema migration output: runtime `pulse-migrate.log`.

HTTP/socket behavior and actual browser interactions have separate acceptance evidence. Passing Python tests alone does not establish browser usability, multi-browser collaboration, or production deployment readiness.
