# Email notifications and reminders

Pulse uses the site's existing Frappe outgoing Email Account and email queue.
No separate Pulse SMTP credentials are required. A working outgoing account,
scheduler and email workers are required; configuring an account alone does not
prove delivery.

Assignment and completion emails use Enable Email Notifications in Pulse Settings.
They require an existing, enabled User with an email address; missing or disabled
accounts are skipped instead of falling back to an old assignment identifier.
Advance reminders use Enable Advance Task Reminders and Days Before Due Date in
Pulse Settings. The default is `3, 1, 0`: three days before, one day before, and on
the due date. They run daily in the site's timezone, not at a chosen clock time.
Apply normal site migration on deployment to install these settings and register
the scheduler hook.

Advance and overdue reminders use native Notification Log alerts. Email delivery
respects each recipient's Frappe notification settings. Recipients must be enabled,
assigned to the task, and currently permitted to read it. Archived, completed and
cancelled tasks are excluded. Advance reminders have deterministic identities per
task, recipient, due date and threshold, preventing duplicate queueing on retries.
Rescheduling a task permits reminders for its new due date.

Advance reminders also appear in Pulse's inbox as Due Reminder notifications,
with the same permission filtering and read/unread controls as other updates.
Their stable identities prevent duplicate inbox entries on a scheduler retry.
The due-date query covers the complete site-local day for both Date and Datetime
fields, including ERPNext sites with a customized task due-time field.

Validation: two real-backend reminder integration tests passed, including repeat
execution and denied access; four email queue tests passed, including escaped
content, disabled/missing/addressless recipients and nonblocking queue failure.
The latest focused run used the isolated Frappe QA site's runner and passed in
0.001 seconds; log: `../.work/pulse-bench/pulse-email-recipient-tests.log`.
Email sending was mocked; these results do
not establish inbox delivery. Local QA has no outgoing account.

## Connected ERP readiness — 2026-09-16

Read-only checks through the user's ERPNext MCP connection confirmed:

- `ERP Notifications` is enabled for outgoing mail and is the default outgoing
  Email Account. No SMTP credentials were read or changed.
- The five most recent Email Queue entries, created on September 15, have status
  `Sent`. This establishes historical queue processing, not recipient inbox
  delivery or delivery of a Pulse notification.
- `frappe.email.queue.flush` and `frappe.email.queue.retry_sending_emails` are
  not stopped and have September 16 execution timestamps. Other daily email
  jobs also have September 16 timestamps.
- No Scheduled Job Type matched `pulse.%`. Pulse's new reminder hook therefore
  remains a deployment prerequisite on the connected site.

The existing default account can be reused. After deploying and migrating,
verify the `pulse.scheduled.reminders.send_advance_reminders` job is registered,
enable the desired Pulse reminder settings, and inspect its execution and queue
results. A real recipient delivery check is still outstanding; the readiness
inspection sent no messages and changed no production settings.
