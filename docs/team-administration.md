# Team administration

Open **Projects → project actions → Manage team**. Pulse Admin and System Manager
can manage existing project members and transfer project ownership, subject to native
Project write permission. Ownership transfer requires an existing enabled system user
who is already a project member, and persists an audit entry.

Removing a project member closes their open native Task assignments in that project,
optionally handing them to another member. It removes project membership and native
Project shares. It does not disable the ERP account or remove separate Task shares.

## New-user invitations

System Manager can create a user from the invitation section. The user receives only
the native **Projects User** role plus **Pulse Junior Developer**, the standard
contributor role needed to read Pulse labels, dependencies and modules, and membership
in the selected project. No administrative role is granted. Other ERP
roles stay in ERP User administration. Existing accounts are rejected rather than
silently upgrading their roles; use Add existing member instead. Existing users need
a Pulse contributor role configured in ERP User settings to use the full workspace.

The native welcome email is queued with a password setup link. Pulse does not expose
the link or set an initial password. A mail-queue failure rolls back the account and
membership. Queueing is not proof of recipient inbox delivery.

## Organization-wide offboarding

System Manager chooses a departing account and an enabled system user to receive its
work, then reviews a plan before applying it. The plan includes all affected Project
ownership/memberships, open native ERP assignments, direct record shares, and enabled
Pulse External Share grants. The replacement joins the affected projects. Owned
projects transfer to the replacement; tasks and their creator/history remain intact.

The apply operation rejects a changed preview. It checks native write/share permission
for every affected record, removes direct shares and external grants, and disables the
native ERP account. It never deletes a User. Re-enabling the account does not restore
revoked project memberships or external grants. Review retained ERP roles before any
reactivation. HR, payroll and accounting records are outside this operation.

Guest, Administrator, the acting user's own account, and users still holding System
Manager are protected. A System Manager account must first have that privilege removed
through ERP user administration. Website Users can be offboarded; replacement users
must be enabled System Users.

Native User validation can end sessions by committing internally. Pulse defers that
session effect until the handoff transaction commits, while retaining native User
validation and notification settings. A postcommit session-cleanup failure is recorded
in Error Log as **Pulse offboarding session cleanup failed**. The disabled account
cannot log in; an administrator can retry native session cleanup.

## Transactions and concurrency

The shared `pulse.services.atomic.atomic_scope` stages Frappe's commit/rollback
callbacks as well as a database savepoint. A caught failure followed by an outer commit
cannot enqueue notifications from the rolled-back handoff. Nested successful scopes
are discarded with a failed parent scope. The helper must only wrap handlers which do
not commit internally.

Open native ToDo assignments and Pulse assignment validation lock and check the target
User row, even when hierarchy is disabled or the actor is Administrator. Offboarding
locks the departing/replacement users before current locking reads of its final scope.
Closing assignments remains possible after a user has been disabled.

## Validation recorded locally

- Expanded team integration suite: 18 tests passed against isolated Frappe/ERPNext.
- Callback staging: four isolated unit tests passed.
- Assignment enabled-user locking: three isolated unit tests passed; the existing
  fourteen permission policy unit tests also passed.
- The integration suite mocks outbound mail and never sends production invitations.
- Final UI build/browser acceptance is coordinated by the parent release task.
