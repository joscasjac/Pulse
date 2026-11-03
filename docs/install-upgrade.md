# Install and upgrade Pulse

Pulse adds project-delivery UI and APIs to an existing ERPNext site. Native ERPNext
Project, Task, assignments and Timesheet records remain canonical. Frappe CRM is
optional; its CRM Task records remain separately owned by CRM.

## Compatibility and installation

The tested baseline is Frappe 16.34.0 with ERPNext 16.35.0. Use compatible v16
releases and a configured ERPNext Company; the test evidence does not establish
compatibility with other major versions. Follow the Frappe/ERPNext installation
procedure for the operating system before installing this app. The repository
includes MIT licensing and requires ERPNext.

On an isolated staging bench, fetch the intended published Pulse branch or release,
record its commit, then install and build:

```sh
bench get-app https://github.com/joscasjac/Pulse.git --branch <published-branch>
bench --site <staging-site> install-app pulse
cd apps/pulse/frontend
npm ci
npm run build
```

Run `bench --site <staging-site> migrate` from the bench directory. Open `/pulse`
and verify a permitted user can create a project and a task. The frontend build
writes the assets and page used by the Frappe site; a stale asset build can hide
new functionality even when backend code is current.

## Upgrade with a recoverable checkpoint

1. Record current Frappe, ERPNext, Pulse and optional CRM versions/commits. Keep the
   matching application checkouts available for rollback.
2. Back up the site's database and public/private files using
   `bench --site <site> backup --with-files`. Retain the site encryption key and
   configuration securely so restored encrypted secrets remain usable. Do not put
   those files in source control.
3. Restore a copy to staging, deploy the intended code, build its frontend, and run
   `bench --site <staging-site> migrate`. Test permissions, native Task edits,
   assignments, files, notifications and optional integrations against that copy.
4. Run the same release build and migration on the target site using its normal
   Frappe Cloud or self-hosted deployment process. Restart application workers
   through that platform. Do not run a development server in production.
5. Verify scheduled jobs are registered and running, inspect failed jobs/error logs,
   then check the frontend and automation workflows as ordinary and restricted users.

A database migration is not rolled back by checking out older code. If an upgrade
fails, stop further writes and restore the pre-upgrade database and file backups
with the matching pre-upgrade app versions using the platform's restore procedure
(`bench restore --help` describes flags for self-hosted benches). Rehearse restoration
on staging. A restore can discard records created after the checkpoint.

Legacy Pulse data requires the separate [legacy migration guide](legacy-migration.md).
Rehearse migration first. Native Timesheet drafts are not silently submitted or billed.

## Validation

On a disposable site with Frappe tests explicitly enabled:

```sh
bench --site <test-site> run-tests --app pulse
```

The runtime and browser evidence in this repository name the tested versions and
limitations. A green unit suite does not verify a production SMTP account, browser
behavior, worker execution, optional CRM installation or every company permission
configuration.

## Safe demonstration data

Use a disposable evaluation site, never a production customer database. Enable
`pulse_demo_mode` explicitly using site configuration, then run:

```sh
bench --site <demo-site> set-config pulse_demo_mode 1
bench --site <demo-site> execute pulse.demo.seed
bench --site <demo-site> set-config pulse_demo_mode 0
```

The generator requires Administrator and refuses to run without the opt-in. It
creates a clearly labeled synthetic native project, three tasks, a module and a
checklist. Repeating it reuses these records; it creates no User accounts, assigns
no recipients, and does not send email. It refuses to adopt an existing project
with the demo name unless the demo marker matches. Dates are initialized relative
to the site's date on first creation.

The legacy showcase seeder targeted retired records and its blanket deletion
routine is disabled. No automatic cleanup deletes business data. Delete only
explicitly identified demo records through normal administration on the disposable
site, or discard the entire evaluation site using the hosting platform's controls.
