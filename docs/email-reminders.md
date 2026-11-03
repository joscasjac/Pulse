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
`pulse.scheduled.reminder_email.queue_reminder_email`.

Advance identities are stable per task, recipient, due date and configured threshold.
Overdue identities are stable per task, recipient, due date and site-local reminder
day. Retries do not duplicate inbox notices or reset their read state. Rescheduling
permits a notice for the new due date; another overdue day permits its daily notice.

Before queueing, Pulse locks and re-reads the User, Task and notification. It verifies
current assignment, enabled account/email, current due date, task lifecycle, row access,
readable/unmasked subject and due-date fields, and email preferences. Title/due fields
which the recipient may not read are also excluded from inbox creation.

The native Email Queue row and the inbox notice's `email_queued` marker commit together.
The marker is set only after an actual queue row exists. A queue attempt failure rolls
back that attempt, keeps the inbox/read state and remains eligible for a scheduler
retry; Error Log records **Pulse reminder email queue failed**. Once queued, subsequent
SMTP failure/retry belongs to the existing native queue entry. Queueing is not SMTP
acceptance, and SMTP Sent is not confirmed inbox receipt.

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

The new explicit scheduled-reminder email implementation is local and not deployed.
After the final release build and normal site migration, verify both reminder jobs,
workers and settings, then run the separately authorized scheduled-recipient test.
Inspect its Pulse Notification/queue reference, native processing status and actual
recipient inbox. Production scheduled reminder delivery through ERP Notifications
remains pending; no second test message is claimed by this document.
