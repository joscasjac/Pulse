# Email notifications and reminders

Pulse uses the site's existing Frappe outgoing Email Account and Email Queue. No
separate Pulse SMTP credentials are required. A working account, scheduler and email
workers are all required; an account's configuration alone is not delivery evidence.

## Settings and recipient checks

Enable Email Notifications in Pulse Settings controls assignment, completion and
scheduled reminder emails. Recipients must be existing, enabled ERP users with an
email address. Missing, disabled and addressless accounts are skipped.

Advance reminders also require Enable Advance Task Reminders. Days Before Due Date
defaults to `3, 1, 0`: three days before, one day before and on the due date. The daily
job uses the site's timezone and the complete local due-date day. It does not promise
a user-selected clock time. Overdue reminders run daily without changing Task status.
Archived, completed and cancelled tasks are excluded.

Reminder email respects the recipient's enabled Notification Settings and email
**event-reminder feature** preference. On supported Frappe versions Pulse calls the
native feature-preference helper; its compatibility fallback checks the global email
and event-reminder fields. Missing preference rows retain native default-on behavior.
The native notification-type allow-list is not the reminder-email switch.

## Inbox and explicit email queue

Advance and overdue reminders write both Pulse Due Reminder inbox notifications and
native Notification Log Alerts. **Frappe Alert logs do not send reminder email by
themselves.** Pulse therefore queues reminder email explicitly through
`pulse.scheduled.reminder_email.queue_reminder_email` for advance reminders and
`pulse.scheduled.overdue_digest.queue_overdue_digest` for overdue summaries.

Advance identities are stable per task, recipient, due date and configured threshold.
Overdue identities are stable per task, recipient, due date and site-local reminder
day. Retries do not duplicate inbox notices or reset their read state. Rescheduling
permits a notice for the new due date; another overdue day permits its daily notice.

Overdue **email** is one summary per recipient per site-local day, containing all
currently eligible overdue tasks, ordered by due date then task ID. Every task has
its own Pulse link and due date. Users with zero eligible overdue tasks receive no
email and no summary marker, including when all previously overdue work is completed.
Per-task inbox notices remain available and retain their read state. A separate daily
Pulse Due Reminder summary notice (`pulse-overdue-digest-<hash>`, linked to `/pulse`)
serves as the queue marker and Email Queue reference. Its identity depends only on
recipient and day: reassignment, a changed due date, or newly overdue work does not
send a second email that day. Advance-reminder behavior and the daily schedule are
unchanged.

Before queueing advance reminders, Pulse locks and re-reads the User, Task and notification. It verifies
current assignment, enabled account/email, current due date, task lifecycle, row access,
readable/unmasked subject and due-date fields, and email preferences. Title/due fields
which the recipient may not read are also excluded from inbox creation.

The native Email Queue row and the inbox notice's `email_queued` marker commit together.
The marker is set only after an actual queue row exists. A queue attempt failure rolls
back that attempt, keeps the inbox/read state and remains eligible for a scheduler
retry; Error Log records **Pulse reminder email queue failed**. Once queued, subsequent
SMTP failure/retry belongs to the existing native queue entry. Queueing is not SMTP
acceptance, and SMTP Sent is not confirmed inbox receipt.

For overdue summaries, the User lock serializes attempts for one recipient. Tasks
are re-read under locks in stable ID order and checked against current assignment,
lifecycle, strictly overdue due date, permissions, field visibility, and preferences.
The daily summary's unique name also prevents duplicates from overlapping stale
snapshots. Queueing also rejects any silent hash-autoname collision rename from
Frappe and rolls it back before creating email. The summary record, Email Queue row and `email_queued` flag are one atomic
savepoint; errors roll back all three and remain retryable. No summary record is
created for an empty result. Native queue retries reuse the existing email. Failed
attempts log **Pulse overdue digest queue failed**. The per-task overdue notices no
longer carry email queue markers; only the daily summary does.

## Local digest validation — 2026-11-05

The focused database-free suite passes 20 tests across `test_overdue_digest_unit`,
`test_scheduled_unit`, and `test_reminder_email_unit`. Coverage includes 81 tasks split
59/22 across two users producing two emails, same-day and next-day identities,
current access/lifecycle/preferences, empty and all-completed results, escaped text,
failed queue rollback/retry, and a simulated stale concurrent identity collision.
The unit email calls are mocked. The existing isolated QA MariaDB/Redis services
were then started on loopback ports 13316/16316 and all 10 database-backed integration
tests passed, using this checkout with SMTP and EmailQueue.send blocked. These cover
real queue rows, daily grouping, empty/completed results, failure-after-queue rollback,
and an actual duplicate-key collision that exercises Frappe's hash-name fallback and
rolls back the renamed record before email. The collision test injects a stale identity
read; it is not a simultaneous multi-worker load test. An initial integration run
failed only because its test searched encoded MIME without decoding it; the corrected
suite passes. Test fixtures roll back, and the services started for this run are stopped.
Evidence is retained in `../pulse-digest-integration-results.txt` and the reproducible
SMTP-blocked wrapper `../run-pulse-digest-integration.py`.

Deployment requires the normal reviewed and authorized Pulse release. No schema migration is required by this change. Avoid manually rerunning the
job on a rollout day after the old per-task emails have already gone out: legacy
per-task markers do not count as the new daily digest marker. This change neither
retracts old emails nor modifies already queued messages or task records.

## Local validation — 2026-11-03

Seven real-backend scheduled reminder integration tests pass, including an actual
Email Queue row without enabling Alert email, duplicate suppression, preferences,
queue rollback/retry, access denial, disabled recipients, changed dates/assignments,
completion and field masking. Ten focused reminder unit tests also pass. Relevant logs
are `../.work/pulse-bench/pulse-reminder-email-tests.log` and
`../.work/pulse-bench/pulse-reminder-unit-tests.log`.

The isolated QA site has no real outgoing SMTP account. Tests exercise native queue
creation with controlled fixture configuration and mocked external sending; they do
not establish production inbox delivery.

## Production evidence and release follow-up

The last recorded production release installed Pulse `8844ab3` on September 16 after
Frappe Cloud deployment and migration. Settings confirmed email notifications and
advance reminders enabled with `3, 1, 0` thresholds. All six Pulse Scheduled Job Types
were registered and not stopped. November 3 read-only checks found execution timestamps,
superseding the earlier September observation of null timestamps. General historical
Email Queue records have Sent status.

The default outgoing account was recorded as **ERP Notifications**. A single authorized
transport test on November 3 reached `joscasjac24@gmail.com` in INBOX. It used the
existing **Joseph - Quest Media** account through the native composer and Send Now:
Communication `e9ehd9thbp`, Email Queue `e9el3g93p0`, Gmail message `1a1a251920cb8ca4`.
This confirms that transport path only.

The explicit scheduled-reminder implementation was deployed on November 3. The
single authorized production test used Task `TASK-2026-00118`, assigned to
`joseph@questmediahub.com`, due November 4. The actual advance-reminder job completed
at 12:59:16 (Scheduled Job Log `8lhb6t462n`). It created exactly one stable Pulse
Notification and Email Queue `8lhj2evh3c` through **ERP Notifications**.

The ordinary `frappe.email.queue.flush` scheduler processed the queue at 13:04:06;
no Send Now action was used. The queue and recipient show Sent. Gmail independently
showed one matching message in INBOX at 13:04, from
`notifications@noreply.questmediahub.com` to `joseph@questmediahub.com`, with the
correct native task link. Sender details showed TLS and the expected signing domain.
Screenshot: `/tmp/pulse-scheduled-reminder-inbox-proof.png`.

The test task was completed at 13:06:21 so it cannot generate subsequent due/overdue
reminders. No further test email is authorized or needed. This verifies the deployed
job, stable notification, real account, automatic queue processing and inbox receipt;
it does not guarantee future delivery independent of SMTP/provider availability.
