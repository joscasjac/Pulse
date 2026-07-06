# Pulse — Deployment Guide

**Document 17 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26 · App `pulse` · Module `Pulse`
**Governing rule:** Reuse-first, upgrade-safe. Pulse installs via standard `bench` tooling; all extensions ship as fixtures — no core edits.

---

## 1. Prerequisites

Pulse is an ERPNext app; it requires a working Frappe/ERPNext v16 bench.

| Component | Required version | Notes |
|---|---|---|
| **Frappe** | v16.25.x | framework |
| **ERPNext** | v16.26.x | Pulse extends Project/Task/Timesheet — ERPNext is **required**, not optional |
| **Python** | 3.11+ | matches Frappe v16 |
| **Node.js** | 18 or 20 LTS | for `bench build` / SPA (Phase 2) |
| **Yarn** | 1.x | asset build |
| **Redis** | 6+ | cache, queue, socketio |
| **MariaDB** | 10.6+ | `utf8mb4`, `barracuda`, `innodb_file_per_table` |
| **wkhtmltopdf** | 0.12.6 (patched Qt) | PDF/print (release reports later) |
| **bench (CLI)** | latest | Frappe Bench |

> Pulse depends on ERPNext. Attempting `install-app pulse` on a bench without ERPNext will fail dependency resolution (Project/Task doctypes and the custom-field targets won't exist).

---

## 2. Install steps

From the bench directory (`/home/ayush/frappe/frappe` on this WSL bench):

```bash
# 1. Fetch the app source into the bench
bench get-app pulse https://github.com/<org>/pulse --branch main
#    (or: bench get-app /path/to/local/pulse for local dev)

# 2. Install onto the target site (installs Pulse + syncs fixtures)
bench --site <site> install-app pulse

# 3. Apply schema (new doctypes, custom fields) and run patches
bench --site <site> migrate

# 4. Build front-end assets (bundles; SPA in Phase 2)
bench build --app pulse

# 5. Clear cache so new workspace/fixtures show
bench --site <site> clear-cache
```

`install-app` runs Pulse's `after_install` hook, which (post-fix — see §12) loads the workspace from the correct path and seeds Pulse Settings defaults + default Role Ranks. It is **idempotent**: safe to re-run.

---

## 3. Fixtures sync

Pulse ships its extensions as fixtures (custom fields, Task Types, roles, workflow, dashboard charts, number cards, Pulse Settings defaults, Role Ranks). Fixtures are applied automatically on `install-app` and `migrate`. To re-sync explicitly (e.g., after pulling new fixtures):

```bash
bench --site <site> migrate                 # applies fixtures + patches
# or, to export fixtures during development:
bench --site <site> export-fixtures --app pulse
```

Fixtures are declared in `pulse/hooks.py` under `fixtures = [...]` (Custom Field filtered to `pulse_*` and the Task/Project targets; Workflow "Pulse Task Workflow"; Task Type records; Roles `Pulse *`; Number Cards; Dashboard Charts). Filter fixtures so they never export unrelated site data.

---

## 4. WSL-specific notes

This bench runs on **WSL Ubuntu 24.04**. Practical guidance:

- **Run bench from inside the WSL filesystem** (`/home/ayush/frappe/frappe`), not a `/mnt/c/...` Windows path — Windows-mounted paths are slow and cause file-watch/permission issues.
- **Redis + MariaDB** run inside WSL; ensure the WSL distro's services are up (`sudo service mariadb start`, `sudo service redis-server start`) or use `bench setup supervisor` for production.
- **Editing files from Windows** (e.g., `\\wsl.localhost\ubuntu-24.04\...`) is fine for docs, but let bench own permissions; avoid `chmod`/`chown` churn from the Windows side.
- **Ports:** default `8000` (web), `9000` (socketio); ensure they're free in WSL. `bench start` binds inside WSL and is reachable from Windows at `localhost`.
- **Line endings:** keep LF (`.gitattributes`), since Frappe tooling and shell scripts expect Unix line endings.
- **Node/Yarn** installed inside WSL (via nvm), not the Windows host.

---

## 5. site_config.json

Per-site config lives at `sites/<site>/site_config.json`. Relevant keys:

```json
{
  "db_name": "...",
  "db_password": "...",
  "encryption_key": "...",
  "maintenance_mode": 0,
  "pause_scheduler": 0,
  "developer_mode": 0
}
```

- Keep `developer_mode: 0` in production (1 only on dev benches, where it lets you edit doctypes/export fixtures).
- Pulse-specific runtime configuration lives in the **Pulse Settings** single doctype (default sprint length, board type, hierarchical-assignment toggle, notification toggles, role ranks, working-days source) — **not** in `site_config.json`.

---

## 6. Enabling the scheduler

Pulse precomputes some metrics (velocity/burndown snapshots) via scheduled jobs (analysis §25–§26). The scheduler must be enabled:

```bash
bench --site <site> enable-scheduler
bench --site <site> doctor            # verify scheduler + workers healthy
```

In production the scheduler runs under supervisor (`bench setup supervisor`). Confirm `pause_scheduler` is `0` in `site_config.json`.

> Note: Pulse does **not** ship the old destructive daily "force overdue status" job (Appendix A4 of Doc 0). Overdue is a *derived indicator*, never a forced write.

---

## 7. Production hardening

- Run behind **Nginx + Supervisor**: `sudo bench setup production <user>` (or `bench setup nginx` + `bench setup supervisor`).
- Set `developer_mode: 0`; disable the desk sign-up if not needed.
- **HTTPS:** `bench setup lets-encrypt <site>` (or terminate TLS at a load balancer).
- Multiple gunicorn workers + background workers (`bench setup supervisor` sizes these).
- Restrict DB access; strong `db_password` and `admin_password`; rotate `encryption_key` handling per Frappe guidance.
- Enable Frappe **rate limiting** and CSRF (default); Pulse adds no custom auth (analysis §24).
- Apply OS/Redis/MariaDB security baselines; firewall all but 80/443.

---

## 8. Backup

```bash
# on-demand backup (DB + optionally files)
bench --site <site> backup --with-files

# scheduled backups (cron/supervisor)
bench setup backups        # sets up periodic backups
```

- Backups land in `sites/<site>/private/backups/`.
- Take a **full backup with files before any upgrade or migration** (including the M0 legacy-data migration in Doc 15).
- Store off-host copies; test restore periodically.

---

## 9. Upgrade procedure

```bash
# 1. Backup first
bench --site <site> backup --with-files

# 2. Update apps (Frappe, ERPNext, Pulse) + dependencies
bench update                      # pulls, builds, migrates all apps
#   or granular:
# bench update --pull --patch --build --requirements

# 3. If only Pulse changed:
cd apps/pulse && git pull && cd ../..
bench --site <site> migrate
bench build --app pulse
bench --site <site> clear-cache
```

Because Pulse is fixtures + custom fields + its own module (no core edits), ERPNext upgrades are safe. Always run `bench --site <site> migrate` after any app update so new custom fields/patches apply. See the compatibility matrix in Release Management (Doc 18) before upgrading ERPNext across a major line.

### Rollback

```bash
# put site in maintenance mode
bench --site <site> set-maintenance-mode on

# restore the pre-upgrade backup
bench --site <site> restore /path/to/backup.sql.gz \
      --with-private-files /path/to/private-files.tar \
      --with-public-files /path/to/public-files.tar

# pin app versions back (checkout previous tag/commit) then rebuild
cd apps/pulse && git checkout <previous-tag> && cd ../..
bench --site <site> migrate && bench build --app pulse

bench --site <site> set-maintenance-mode off
```

The legacy-data migration (Doc 15 M0) is data-transforming; its rollback path is **restore-from-backup**, which is why a pre-migration backup is mandatory.

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `FileNotFoundError` during `after_install` | Historical workspace-path bug (see §12) | Ensure you're on the fixed version; workspace loads from `.../workspace/pulse/pulse.json` |
| "Pulse Board" / workspace shortcut 404 | Old build's page had metadata only (Doc 0 A2) | Fixed build reuses Frappe Kanban Board + workspace; rebuild + clear cache |
| Custom fields missing after install | Fixtures not synced | `bench --site <site> migrate`; check `fixtures` in `hooks.py` |
| Workflow states not appearing on Task | Workflow fixture not applied / conflicts with existing workflow | Re-run migrate; ensure no conflicting Task workflow is active |
| Scheduler jobs not running (no burndown snapshots) | Scheduler disabled / paused | `bench enable-scheduler`; `pause_scheduler: 0`; `bench doctor` |
| `AttributeError` on Task sync | Historical wrong-field-name bug (Doc 0 A3) | Not present in re-baselined build — the card *is* the Task, so there is nothing to sync |
| Permission errors on legitimate writes | Correct behavior — no more blanket bypass | Assign proper `Pulse *` role; check `permlevel` and hierarchy rank |
| Assets not updating | Stale build | `bench build --app pulse && bench clear-cache` |

### Historical install path bug (now fixed)

The original build's `install.py` loaded the workspace from `.../workspace/pulse_workspace/pulse_workspace.json`, but the actual file is `.../workspace/pulse/pulse.json` — causing `FileNotFoundError` during `after_install` and blocking clean installs (Doc 0 Appendix A1). **The re-baselined build fixes this** by (a) correcting the path, and (b) shipping the workspace as a plain fixture rather than hand-rebuilding it in Python. If you hit this error, you are on an old build — update to the current release.

---

## 11. Verifying the install

After `install-app` + `migrate` + `clear-cache`, confirm:

```bash
# app is installed on the site
bench --site <site> list-apps           # expect: frappe, erpnext, pulse

# doctypes exist
bench --site <site> console
>>> import frappe
>>> frappe.db.exists("DocType", "Pulse Sprint")            # -> "Pulse Sprint"
>>> frappe.db.exists("DocType", "Pulse Task Status Log")
>>> frappe.db.exists("DocType", "Pulse Settings")
>>> frappe.db.exists("DocType", "Pulse Role Rank")
```

Manual verification checklist:

1. **Roles present:** `Pulse Admin`, `Pulse Manager`, `Pulse Team Lead`, `Pulse Senior Developer`, `Pulse Junior Developer`, `Pulse Intern`, `Pulse Viewer` (Role list).
2. **Workspace present:** the **Pulse** workspace opens (no 404) with Sprint/Board/Backlog/metrics links.
3. **Custom fields present:** open a **Task** — see `Story Points`, `Sprint`, `Epic`, `Backlog Rank`, `Release/Version` under the Pulse section; open a **Project** — see `Enable Scrum`, `Board Type`, `Default Sprint Length`, `Project Key`.
4. **Task Types present:** Epic, Story, Bug, Task, Sub-task, Improvement, Incident, Feature.
5. **Workflow present:** "Pulse Task Workflow" active on Task with states Backlog → To Do → In Progress → In Review → Done (+ Cancelled).
6. **Pulse Settings:** single doc opens with defaults (sprint length 14, board type Scrum, hierarchical assignment on) and default Role Ranks table populated.
7. **Smoke test:** create a Project (Enable Scrum), a Pulse Sprint, a Task with story points, move it across the board — confirm a Pulse Task Status Log row is written.

*End of Document 17.*
