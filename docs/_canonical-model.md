# Pulse ERPNext contract

This fork implements the user-approved ERPNext backlog. This document supersedes the upstream standalone charter and archived design plans.

## Sources of truth

- **Projects:** ERPNext `Project`, extended with Pulse project configuration.
- **Tasks:** ERPNext `Task`, extended with agile state, sprint, rank, points and labels. Preserve native task status semantics separately from configurable board states.
- **Assignments:** Frappe `ToDo` and the framework-maintained task assignment field. Changes use the standard assignment API.
- **Time entries (target):** ERPNext `Timesheet` / `Timesheet Detail`, including billable flags. Existing Pulse time records must be migrated idempotently with provenance; until migration lands they remain legacy data, not a second writable source.
- **Agile extensions:** Pulse owns sprint history, dependencies, checklists, intake requests, documentation and saved views linked to native projects/tasks.

## Integrity and permissions

Every user-facing list and aggregate must respect the same record visibility as detail and mutation APIs. Writes use document validation; internal migration/history writes require an explicit, narrow trusted path. Realtime events must not disclose inaccessible records. Existing task relationships and historical data must survive migrations.

## Runtime

ERPNext is required. Use app custom fields, DocTypes and hooks without modifying ERPNext core. Install/migrate operations must be idempotent. Real Frappe/ERPNext integration tests, including restricted users, are required before release.

## Delivery

See `BACKLOG.md` for the complete implementation scope and evidence status. A schema or mock test alone does not prove a usable feature.
