# Company-readiness validation — 2026-11-03

## Release state

The additions below are implemented locally. They have **not been deployed** to the
production site. Local test and browser acceptance is not production acceptance.
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

The latest complete Pulse run passed **193 integration tests** in 42.405 seconds,
plus **73 additional tests**, with one environment skip. Log:
`../.work/pulse-bench/pulse-readiness-final-tests.log`.

Narrow changes after that run were checked separately:

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
of every screen or production setup. Frontend production builds passed during this
implementation; a final release build must match the final backend changes.

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

## Production email evidence and pending checks

Production Pulse jobs have November 3 execution timestamps and are not stopped. The
site's default outgoing account was recorded as ERP Notifications. Neither observation
proves scheduled Pulse reminder inbox delivery.

One authorized transport test was sent to `joscasjac24@gmail.com` using the native ERP
Communication composer. Communication `e9ehd9thbp` and Email Queue `e9el3g93p0` show Sent
with no error. The selected account was **Joseph - Quest Media**, and Send Now processed
that queue entry. Gmail confirmed the exact message in INBOX (`1a1a251920cb8ca4`). This
proves that account's transport and receipt, not automatic queue timing, the default
ERP Notifications account, or scheduled Pulse reminder execution.

The true scheduled reminder test and deployment are still pending. The earlier Quest
rich-email editor stale-callback defect has a local fix; its final browser regression
check remains separate from the successful native-composer transport test. Earlier
editor image-upload acceptance remains blocked by Chrome extension file-URL access;
no successful image upload is claimed here.

## Final merged regression — 2026-11-03

The final Pulse full-app run passed **194 integration tests and 73 additional tests**
(one optional CRM test skipped in this bench; the separate installed-CRM suite passed
6 tests). Quest Automations passed **91 unit tests and 3 real Frappe worker tests**
after integrating current upstream AI/live-followup changes. The no-send browser
email-editor regression preserved the recipient and subject while editing the body
and rendered its preview correctly. Browser acceptance found Pulse actions missing
from the action picker despite backend catalog coverage; that UI gap is being closed
before release. Deployment and the authorized production scheduled-email test remain
pending.
