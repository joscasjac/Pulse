# Legacy Project and Task migration

Back up the site before migration. Keep legacy DocTypes and records installed until
all data and linked records have been inspected. This migration never deletes the
source Project/Task or source child rows. Native Project/Task become the operational
records; unusual fields without native equivalents remain available on the legacy
source for manual review. Do not remove legacy tables as a cleanup step.

1. Put the site in maintenance mode and stop workers/schedulers during migration.
2. Run `bench --site SITE backup --with-files` and `bench --site SITE migrate`.
   Custom-field DDL is deliberately separate from transactional data migration.
3. Run the validation rehearsal:
   `bench --site SITE execute pulse.erpnext_bridge.migrate`.
   The default `dry_run=True` performs inserts, validation and reference changes,
   then rolls back to the migration savepoint. Returned names are provisional.
4. Resolve any reported missing links, invalid dates, or required ERPNext setup.
   No ignore_links/ignore_mandatory escape is used. For previously migrated native
   records, inspect the pair manually and set `pulse_legacy_project` or
   `pulse_legacy_task` on the intended native record to the exact legacy name.
   Display names and issue keys alone are not accepted as proof of identity.
5. Apply with `bench --site SITE execute pulse.erpnext_bridge.migrate --kwargs '{"dry_run": false}'`.
6. Inspect Project members, Task hierarchy/epics/labels, ToDo assignees, dependencies,
   checklists, comments, attachments and retained Pulse record links. Compare source
   and native counts and representative records before enabling writes again.
   Migrate legacy time with the separate time migration procedure.

Persistent unique source-name markers make retries safe even without issue keys.
Existing marked native records are not overwritten wholesale on rerun; relationships
are completed and retained references are repaired. Legacy `_assign` is translated
into real open ToDo rows, while existing ToDo history and dynamic links are moved to
the native target. Unknown task/project references and ambiguous identity stop the
transaction. In-process flags are restored after success or failure. A thrown error
rolls back all migration data changes; restoring the backup is the recovery path
once a successful apply has been committed.

A rehearsal proves database validation only; it does not replace browser checks or
comparison against a production backup. Keep all third-party document hooks free of
external side effects during maintenance: database rollback cannot undo external API
calls. Pulse notification and task-history hooks honor `pulse_migration`.
