# Isolated legacy migration fixture

These four schema JSON files are projected from commit `e9a3bd2` in this repository,
which predates ERPNext consolidation. Original fields, source link types, naming,
and child-table shape are retained. Changes: custom=1 permits installation without
restoring old Python controllers; permissions are limited to System Manager;
layout labels are supplied when absent; Pulse Project's holiday_list is omitted
because this fixture does not install the separate legacy holiday subsystem.
The tests make no claim to cover holiday-list migration.

Only run `pulse.tests.test_legacy_migration_integration` on a disposable test site
with site config `pulse_legacy_migration_tests=1`. Setup refuses any pre-existing
legacy schema and teardown deletes only names recorded as created by this class.
Fixture data uses real ORM except retained rows whose link targets intentionally
represent persisted pre-upgrade state; those rows use db_insert. No file bytes or
network access is needed. Tests intercept only the migration's final commit so
rollback clears all fixture data; schema DDL is installed/removed separately.
