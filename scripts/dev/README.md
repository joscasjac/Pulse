# Dev / throwaway scripts

Ad-hoc scripts used during development (schema checks, one-off seeders, demo data).
Run via `bench --site <site> execute` or `bench --site <site> console`.

**Not part of the shipped app** and **not imported by app code.** Some older ones
(e.g. `_create_fy.py`, `seed_all.py`) reference ERPNext doctypes and predate the
standalone re-baseline — they are kept only as history. The supported demo seeder
will be consolidated here in Phase 7.
