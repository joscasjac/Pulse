# Company-readiness validation — 2026-11-03

## Release state

The retained features were deployed to the production site on November 3 (Pulse
`651d9a7`, Quest Automations `8fcc332`, Quest Media Tools `1176adf`). The native
Datetime display correction `1f6e582` was deployed subsequently and its live entry
asset verified. This revision packages the final private-editor upload correction;
its local browser and backend acceptance is recorded below. Release packaging and
production smoke verification are separate from local test results.
Resource/financial planning, management reporting and mobile remain deferred. Sprints,
Intake and Timesheets navigation remains hidden.

## Implemented and tested locally

- Team administration: membership, atomic assignment handoff, audited ownership
  transfer, native new-user invitations and reviewed organization-wide offboarding.
  New accounts receive Projects User and Pulse Junior Developer, without administrative
  privileges. Offboarding rejects stale previews, revokes direct/external grants,
  disables the ERP account and ends sessions after commit. All 18 integration tests
  pass, including the invited account using settings, task detail and modules. See
  [team-administration.md](team-administration.md).
- Business handoffs: CRM/order source ownership stays canonical; stable source mapping
  creates or reuses a native project and template tasks without duplicate delivery.
  Replays, source permissions, native Sales Order links and rollback are tested.
- Company fields and approvals: editable scalar custom fields, project forms and
  status requirements are enforced on native saves and APIs. The full creation form
  accepts required custom values on the first save. Approval decisions use an explicit
  authorized reviewer; stale decisions and bypassing protected status transitions are
  rejected. Active recurring templates prevent incompatible configuration changes.
  [task-company-fields.md](task-company-fields.md) records the supported recurring boundary.
- External collaboration: enabled Website Users see only explicitly shared tasks and
  narrow fields through a separate portal, with separate comments and revocable grants.
  Internal Task access is not granted by a portal share. Revocation and offboarding are
  tested, including a locked grant recheck before comment creation.
- CSV adoption: preview, bounded atomic create/update, replay without duplicate tasks,
  row/field permissions and spreadsheet-safe exports. Configured scalar company fields
  round-trip, including negative numeric values. Restricted export/replay, malformed
  input, concurrent task moves and discarded failure callbacks are tested.
- Reminder delivery: advance and overdue notices have stable inbox identities and an
  explicit native email-queue path. Queue insertion and its marker commit together;
  failure preserves retry eligibility and read state. Recipient lifecycle, assignment,
  due date, task access, field masks and native feature preferences are rechecked.
  See [email-reminders.md](email-reminders.md).
- Automation coverage: 61 bounded Pulse operations and 19 Quest document-event presets
  reuse the native permission-checked APIs. User/field permissions filter event payloads.
  Duplicate events, workflow-chain loops, checkpoint resume and visible failed runs are
  tested. See [automation.md](automation.md) for required inputs and examples.
- Installation and administration documentation now covers compatibility, upgrade and
  restore checkpoints, demo data and administrator checks; see
  [install-upgrade.md](install-upgrade.md). A fresh production upgrade remains pending.

## Validation evidence

The final complete Pulse run passed **195 integration tests** in 28.322 seconds,
plus **73 additional tests** in 0.097 seconds, with the optional CRM test class skipped
in this bench. The final frontend suite passed **16 tests**.
The separate installed-CRM bench passed all six CRM integration tests. Log:
`../.work/pulse-bench/pulse-final-private-image-full-tests.log`.

Supporting focused runs also passed:

- Team default-role usability: 18 integration tests passed in 6.731 seconds,
  `pulse-team-expanded-tests.log`.
- Active recurring configuration guard: one regression passed in 0.366 seconds,
  `pulse-recurring-config-guard-tests.log`.
- Final configured-field CSV round-trip: five integration tests passed in 3.477 seconds,
  `pulse-transfer-final-tests.log`.
- Explicit reminder email: seven real-backend tests and ten focused unit tests pass,
  including queue failure/retry and no dependency on Alert email being enabled.
- Quest Automations: 91 unit tests pass. Three real Frappe worker integration tests
  pass, covering native work creation once, checkpoint resume, duplicate events,
  self-trigger rejection and visible failure without executing later steps.

These counts are evidence for the recorded revisions, not a substitute for acceptance
of every screen or production setup. Frontend production builds passed. The final build must be deployed with its matching
backend revision; generated assets are tracked in the release commit.

## Browser acceptance checkpoint

The parent browser session verified the local CSV preview/import/replay/export flow,
required-status validation, an authorized reviewer approving a task then moving it to
Done, and an isolated Website User commenting on a shared task followed by revocation.
The full New task form also created fixture `PBAN-3` with the required **Acceptance
marker November** custom value, and the drawer showed the persisted value. Team
management's offboarding preview/confirmation/apply flow disabled a synthetic external
account; that browser plan had zero project/assignment handoffs. The nonempty handoff,
invitation and ownership cases are covered by backend integration tests, not promoted
to browser mutations here. Screenshots: `/tmp/pulse-first-save-custom-field-browser.png`
and `/tmp/pulse-team-offboarding-browser.png`.

## Production acceptance and final release evidence

- Frappe Cloud pre-release backup completed November 3 at 12:28 with database,
  public and private files. The core deployment pipeline `cae93d14n0` succeeded;
  the site migration succeeded at 12:57. Pipeline `0p6tsn1d99` then deployed the
  tested native-Datetime display correction; the live entry was `index-BlMgeYZP.js`.
- The live workspace and automation builder loaded successfully after migration.
  All 61 Pulse actions appeared in the deployed picker. Screenshot:
  `/tmp/quest-pulse-live-action-builder.png`.
- Actual scheduled email passed end to end: advance-reminder job log `8lhb6t462n`
  Complete at 12:59; Email Queue `8lhj2evh3c` Sent through ERP Notifications by the
  normal queue scheduler at 13:04; exactly one matching Gmail INBOX message to
  `joseph@questmediahub.com`, with the correct task link. No Send Now was used.
  Task `TASK-2026-00118` was completed afterward to prevent future reminders.
  See [email-reminders.md](email-reminders.md).
- The no-send Quest email-editor browser regression preserved recipient and subject
  while editing the body, then rendered the correct preview.
- The native Datetime fixture displayed **4 Nov** in Home rather than Invalid Date.
  The shared formatter also normalizes My Work due-day grouping. Thirteen frontend
  tests passed at that correction, including native Date/Datetime, malformed values
  and multiple timezone checks. Screenshot: `/tmp/pulse-native-datetime-browser-proof.png`.
- Final private-image browser acceptance passed for a saved Task and collaborative
  page: private URL rendered, save/synchronization completed, and the image remained
  loaded after a full reload. File rows `2ba865a045` and `5fadf61b2e` both have
  `is_private=1` and distinct canonical parents (Task `TASK-2026-00155` and Pulse
  Document `i8gsd5m48g`), sharing a deduplicated content URL. Screenshots:
  `/tmp/pulse-private-task-image-browser.png`, `/tmp/pulse-private-page-image-browser.png`.
- The upload fix uses the installed Frappe UI's supported `private: true` option;
  `is_private` is the HTTP field, not the uploader option. Tests exercise the actual
  installed uploader's multipart request, canonical parent references, private PNG
  storage, persisted HTML and access denial after parent membership is revoked.
  Privacy enforcement was retained. Unsaved pages require creation before uploading.
- Quest Automations now has **100 passing unit tests, 6 frontend tests and 6 real
  worker integration tests**. Added worker acceptance captures an actual Sales Order
  submission hook and shipped preset, creates one native project and two template
  tasks with retained commercial ownership/links, and proves replay does not
  duplicate them. A native Due Reminder insert also runs the shipped preset once.
- The standalone MCP SDK suite passed 3 tests; the ERP connector catalog tests passed
  2. Production `pulse_work` and `custom_tools` remain enabled. **Live client tool-list
  refresh and invocation were explicitly deferred by the user**; no successful
  invocation through this chat's cached tool list is claimed.

Resource/financial planning, management reporting and mobile remain deferred. Sprints,
Intake and Timesheets navigation remains hidden. These tests document the retained
scope and tested v16 baseline; they do not claim universal ERP functionality or
compatibility with untested versions.
