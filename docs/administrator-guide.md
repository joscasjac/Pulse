# Pulse administrator guide

## Start with access

Pulse uses Frappe authentication and native ERPNext document permissions, plus
project-membership and task-scope checks. Configure roles and project membership
before importing or sharing company work. Test with a restricted user; Administrator
visibility does not represent the team's experience. Review attachment access and
optional integrations with the same accounts.

Project team controls are in Projects → project actions → Manage team for authorized
administrators. Use native ERP users; invitations, membership, assignment handoff and
ownership controls must be reviewed together with the current [validation record](company-readiness-validation.md).
Removing project membership does not disable an ERP account or revoke all independently
granted task access. Organization-wide offboarding must also review shares,
assignments and roles. Project ownership transfers write an audit entry.

Sprints, Intake and Timesheets navigation remain hidden by product choice. Existing
records and supported APIs are not removed. Resource/financial-planning expansion,
management-visibility expansion and mobile work are currently deferred.

## Work, documents and templates

List, board, calendar, spreadsheet and timeline views operate on the same native
Task records. Start and due dates, assignments, statuses and task links remain visible
through ERPNext. Project-configured task vocabulary and labels are validated on writes.
Review project settings before changing existing status/type definitions.

Project pages have separate comments, revisions and linked tasks. A project marked
as a reusable template can produce new projects with native tasks and structure.
Use a dedicated template project rather than converting a live delivery project
without review. Template cloning resets execution status and checklist completion;
it does not copy client delivery results as completed work.

## Commercial handoffs

Create delivery work from a submitted Sales Order, CRM Deal or ERPNext Opportunity.
The handoff checks source permission, creates a native Project (optionally from an
existing reusable template), and stores one stable source-to-project mapping.
Repeating a handoff returns its existing project rather than creating duplicates.
Sales Order customer/order links are native Project links. A cancelled source cannot
start delivery. CRM must be installed to use CRM Deal sources.

A handoff does not convert or duplicate CRM Task follow-ups. Those remain CRM-owned;
Pulse's CRM task view updates the original CRM Task with current permissions and
concurrency checks. If a source mapping refers to an inaccessible project, ask an
administrator to review access rather than creating a second delivery project.

## Client and vendor collaboration

Internal users with Task write and share permissions can explicitly grant an enabled
Website User access using External collaboration in task details. The participant
signs in and opens `/pulse/external`. Website users receive a minimal shared-work
surface without the internal workspace sidebar or initialization calls.

A portal grant exposes only the task identifier, title, status, start/due dates and a
separate shared discussion. Internal descriptions, attachments, assignees, project
metadata, dependencies and internal comments are excluded. Shared discussion content
is visible to all participants granted that task, so do not post internal information
there. Comments are rendered as text; no participant-controlled HTML is executed.

Portal grants use Pulse External Share records, not native Task DocShare grants.
They intentionally do not grant full Task or Project access through core Frappe APIs.
Revoke the portal grant to block subsequent reads/comments, or disable the User to
block every portal grant. An independently granted native ERP permission/share has
its own broader effects and must be audited separately.

## Email, reminders and workers

Pulse reuses the site's outgoing Email Account and Frappe email queue. Configure the
default outgoing sender and each recipient's notification preferences. Scheduled
jobs and email workers must be operating; an SMTP account alone is insufficient.

Pulse Settings controls assignment/completion email, advance task reminders and
reminder thresholds. Only enabled, permitted assigned recipients receive reminders;
completed, cancelled and archived tasks are excluded. Advance and overdue jobs use
stable notification identities so reruns do not duplicate the same reminder.

After deployment/migration, inspect Scheduled Job Type and job logs for Pulse jobs,
then inspect the exact Communication/Email Queue records produced by an authorized
test. `Sent` means SMTP acceptance; recipient inbox receipt is a separate observation.
The November test documented in the validation record reached Gmail through the
Joseph account. It does not establish the ERP Notifications account or automatic
scheduled reminder execution. See [email reminders](email-reminders.md) for details.

## Automations and support

Quest Automations is a separate app. Its actions call permission-checked Pulse domain
APIs as the workflow's publishing user. Review the catalog and deployed version before
publishing a workflow; new local actions are unavailable until their code is deployed.
Use stable source identities for handoffs and inspect failed/needs-attention runs before
retrying side effects. Trigger chains prevent rerunning a workflow in its own chain.

Keep failed-job, error-log and email-queue access limited to administrators. Back up
before upgrades and rehearse restore using the [install/upgrade guide](install-upgrade.md).
Report the app versions, exact operation and a redacted error reference when requesting
support. Do not include SMTP passwords, API secrets, site encryption keys or private
customer content in issue reports.
