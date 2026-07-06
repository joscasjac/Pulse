# Pulse — Release Management

**Document 18 of 21**
**Product:** Pulse — Modern Project Management for ERPNext
**Platform:** Frappe v16.25 · ERPNext v16.26 · App `pulse` · Module `Pulse`
**Governing rule:** Reuse-first, upgrade-safe. Releases ship fixtures + custom fields + the four Pulse doctypes — never core edits.

---

## 1. Semantic versioning

Pulse follows **SemVer 2.0.0** — `MAJOR.MINOR.PATCH`:

- **MAJOR** — breaking changes: removing/renaming a custom field or doctype, changing a whitelisted API contract, removing a workflow state, or completing deprecation of the legacy `Pulse *` doctypes.
- **MINOR** — backward-compatible features: new views, new metrics/reports, new optional custom fields, new API endpoints.
- **PATCH** — backward-compatible fixes: bug fixes, fixture corrections, docs.

Milestones map to versions: **v1.0.0** = Phase 1 MVP gate (Doc 15 M1); **v2.0.0** = Phase 2 SPA GA; **v3.0.0** = Phase 3 ecosystem. Pre-releases use `-alpha.N` / `-beta.N` / `-rc.N`.

The version lives in `pulse/__init__.py` as `__version__` and is git-tagged `v<version>`.

---

## 2. Git branching model

A lightweight GitHub-flow variant suited to a small OSS maintainer team:

- **`main`** — always releasable; protected; every merge is green in CI.
- **`develop`** *(optional, used from Phase 2 when parallel work grows)* — integration branch.
- **`feature/<epic>-<short>`** — one epic/story per branch, PR into `main` (or `develop`).
- **`release/<x.y>`** — cut when stabilizing a MINOR/MAJOR; only fixes land here.
- **`hotfix/<x.y.z>`** — branched from the release tag for urgent production fixes.

Rules: no direct commits to `main`; squash-merge PRs; every PR passes the checklist in Coding Standards (Doc 19) including the **reuse gate**. Tag releases on `main` after merge.

---

## 3. Changelog & release notes template

Keep a `CHANGELOG.md` (Keep-a-Changelog format), grouped by type, newest first.

```markdown
## [1.1.0] - 2026-09-15

### Added
- Burnup chart and Cumulative Flow Diagram (reuses Dashboard Chart engine).
- `pulse_release` grouping on Task.

### Changed
- Board API payload trimmed for faster 500-card loads.

### Fixed
- Burndown working-day calc now respects the configured Holiday List.

### Deprecated
- `Pulse Milestone` doctype (migrate to Task `is_milestone`). Removal in 2.0.0.

### Reuse notes
- Burnup/CFD built on Frappe reporting engine — no new charting code.

### Compatibility
- Frappe v16.25+ · ERPNext v16.26+
### Migration
- Run `bench --site <site> migrate`. No manual steps.
```

Release notes (GitHub Releases) summarize highlights, upgrade steps, and any breaking changes for humans.

---

## 4. Frappe / ERPNext compatibility matrix

Every release declares supported framework versions. Pulse **requires ERPNext** (it extends Project/Task/Timesheet).

| Pulse | Frappe | ERPNext | Python | Node | Status |
|---|---|---|---|---|---|
| 1.0.x | v16.25+ | v16.26+ | 3.11+ | 18/20 | current |
| 1.1.x | v16.25+ | v16.26+ | 3.11+ | 18/20 | planned |
| 2.0.x | v16.x (latest) | v16.x (latest) | 3.11+ | 18/20 | planned (SPA) |

Policy: support the current Frappe/ERPNext v16 line; add a **next-version CI job** early to catch upgrade breakage (analysis §27 risk). Dependency declared in `pulse/hooks.py` (`required_apps = ["erpnext"]`) and documented per release.

---

## 5. Release checklist

Before tagging any release:

- [ ] All PRs merged; CI green (lint + install + migrate + unit/integration/permission tests — Doc 16).
- [ ] Clean install verified on a fresh bench (`install-app` → `migrate` → verify steps in Doc 17 §11).
- [ ] Upgrade verified from the previous release (backup → update → migrate).
- [ ] Fixtures re-exported and diffed (custom fields, Task Types, workflow, roles, charts) — no stray site data.
- [ ] `__version__` bumped; `CHANGELOG.md` updated; compatibility matrix updated.
- [ ] Migration/patch scripts idempotent and tested (esp. legacy `Pulse *` migration).
- [ ] Docs updated (Deployment, this doc, README).
- [ ] Breaking changes called out; deprecations dated.
- [ ] Tag `v<version>` on `main`; publish GitHub Release with notes.
- [ ] Announce (forum/discussion + community roadmap).

---

## 6. Hotfix flow

1. Branch `hotfix/<x.y.z>` from the affected release tag.
2. Minimal fix + regression test; bump PATCH; update CHANGELOG.
3. CI green; verify on a site reproducing the bug.
4. Merge to `main` (and `develop`/active `release/*` branches — no divergence).
5. Tag + publish; notify affected users with clear upgrade steps (`bench update` / `git pull` + `migrate`).

Hotfixes never introduce new features or new doctypes.

---

## 7. Deprecation policy (legacy `Pulse *` doctypes)

The parallel doctypes are deprecated (canonical §1; analysis §18). Timeline:

| Stage | Version | Action |
|---|---|---|
| **Announce + provide migration** | 1.0.0 | Legacy doctypes marked deprecated; one-time migration script ships (Doc 15 M0) migrating data → core Task/Project. |
| **Read-only / warn** | 1.x | Legacy doctypes flagged read-only; UI/log warnings direct users to migrate; new work uses core Task/Project only. |
| **Remove** | 2.0.0 | Legacy doctypes removed via a guarded patch (only if migrated); documented in release notes as breaking. |

General deprecation rules:
- Never remove a public API/custom field/doctype in a MINOR/PATCH — only in a MAJOR.
- Deprecations announced at least one MINOR ahead, dated in the CHANGELOG, with a migration path.
- Provide an idempotent patch that migrates or no-ops if already migrated.

---

## 8. Fixtures & versioning of custom fields

- Custom fields, Task Types, workflow, roles, dashboard charts, number cards ship as **fixtures**, versioned in git alongside code.
- Treat a custom field like a public interface: **renaming/removing = breaking (MAJOR)**; add new fields as backward-compatible (MINOR).
- Field changes that need data transformation ship with a **patch** (`patches.txt`) that is idempotent.
- Re-export and diff fixtures on every release (checklist §5) so the shipped schema matches the repo. Filter fixtures narrowly (`pulse_*` custom fields, `Pulse *` roles, the named workflow) to avoid leaking site data.

---

## 9. Publishing (open source)

- **License:** standard permissive Frappe-app license (e.g., MIT/GPL per ecosystem norm); include `LICENSE`.
- **Repo:** public GitHub; clean `README.md` (what Pulse is, reuse-first thesis, install steps); docs site links; issue/PR templates; "good first issue" labels.
- **Install path:** `bench get-app pulse` → `bench install-app pulse` (Doc 17); fixtures applied automatically.
- **Releases:** GitHub Releases with tag, notes, and the compatibility matrix; SemVer tags.
- **CI badge** (install + tests against target Frappe/ERPNext) on the README.
- **Community:** open roadmap (Doc 20), CONTRIBUTING.md + coding standards (Doc 19) including the reuse gate, discussion forum/chat, recognition for contributors.
- **Frappe ecosystem:** aim for listing alongside apps like HRMS/Gameplan/Helpdesk as the reference agile-PM app.

*End of Document 18.*
