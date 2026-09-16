# Pulse for ERPNext

Agile project delivery inside ERPNext, using native **Project**, **Task**, Frappe assignments, and **Timesheet** records. This fork is implementing the [development backlog](BACKLOG.md); unchecked items are not yet verified complete.

## Architecture

- Vue 3 / frappe-ui frontend at `/pulse`.
- Python APIs under `pulse.api.*` and native Frappe document permissions.
- Pulse DocTypes for sprints, dependencies, checklists, documentation and delivery extensions.
- ERPNext is required. See the [canonical model](docs/_canonical-model.md) and [architecture decision](docs/adr/0001-native-erpnext-records.md).

## Development installation

Use an isolated Frappe v16 bench with ERPNext installed and its Company configured:

```sh
bench get-app https://github.com/joscasjac/Pulse.git --branch codex/erpnext-backlog
bench --site your-site install-app pulse
cd apps/pulse/frontend
npm install
npm run build
```

The development branch must be pushed before the command above can fetch it. The committed upstream frontend assets do not represent the current development changes; build the frontend before testing.

## Existing installations

Back up the database and files before upgrading. Run `bench --site your-site migrate` to install schema changes. For installations with legacy Pulse time records, first review a dry run:

```sh
bench --site your-site execute pulse.services.time_migration.migrate
bench --site your-site execute pulse.services.time_migration.migrate --kwargs '{"dry_run": false}'
```

Legacy time records are retained for provenance and become read-only. Migrated entries are native draft Timesheets; they are not silently submitted or billed. Date-only legacy entries receive documented synthetic intervals and native validation can require resolving overlaps before migration succeeds.

## Validation

```sh
python3 -m unittest pulse.tests.test_analytics_unit
bench --site your-test-site run-tests --app pulse
```

Do not treat pure unit tests as evidence of real-backend permissions or financial correctness. Follow the evidence log in `BACKLOG.md`.

## License

[MIT](LICENSE). Forked from [mithtech-is/Pulse](https://github.com/mithtech-is/Pulse).
