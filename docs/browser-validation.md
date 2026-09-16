# Browser acceptance evidence

## Readable label history follow-up — 2026-09-16

Replaced generic child-row counts with named added/removed entries in TaskDrawer.
Chrome on CBA-1 showed Added label: Client review; unchecking the label then
displayed Removed label: Client review, with Administrator and timestamps.
Field names now distinguish ERPNext status from workflow Status and use Archived
instead of pulse_archived. This supersedes the generic-label-summary limitation
recorded below. Names resolve from authorized current project labels; unavailable
or moved-away labels show an explicit unavailable fallback without fetching other
projects. Build `/tmp/pulse-activity-build.log` passed; focused detector had no
findings. Names reflect the current label vocabulary, not a historical name snapshot.

## Task types, colored labels and activity — 2026-09-16

Created Client review with color #008080 in PROJ-0131 task settings. Opened
CBA-1, selected Milestone and applied that label; close/reload/reopen retained
both. Activity displayed Administrator and timestamp for the Type → Milestone
change and a child-row addition for the label. The latter is currently a generic
added-row summary, not the label's readable name.
Configured allowed types to Bug, Task, Feature and Milestone, saved, then reopened
the task: the Type selector offered exactly those four choices. This establishes
configuration and editor filtering, plus a persisted Milestone change; it does
not claim separate creation scenarios for every type or mention email delivery.

## Bulk edit, archive and restore — 2026-09-16

Created CBA-1/CBA-2 (Bulk acceptance one/two) through the inline Kanban creator
in synthetic project PROJ-0131. Selected both with their named checkboxes, applied
In Progress and High in one bulk action, and observed both cards updated.
Selected and archived both: active count became zero and both cards disappeared.
Enabled Include archived, selected the retained cards, and restored both.
Disabled Include archived and reloaded: both cards remained visible with
In Progress/High. Fixtures are retained in QA. This exercises real Administrator
bulk edit/archive/restore; bulk assignment, cross-project movement and relation-rich
preservation remain separate browser scenarios (with existing backend coverage).

## Workflow order, name and color — 2026-09-16

Source inspection found Task settings lacked a status-order interaction despite
the backend preserving row order. Added Up/Down controls with named accessible
labels and disabled boundary/saving states. In Chrome on PROJ-0131, moved To Do
above Backlog, renamed it Ready, set its color to #008080 and saved. The list
groups immediately followed that order. After reload, Kanban displayed Ready
first, Backlog second; reopening settings retained the name, order and color.
Desktop screenshot inspection confirmed aligned controls and colored columns.
Production build passed (`/tmp/pulse-status-order-build.log`); the Impeccable
detector reported no findings for the changed component. This is Administrator
workflow configuration evidence; restricted-role configuration is separate.

## Allocation and leave capacity acceptance — 2026-09-16

Using the Chrome Workload UI and its native creation dialogs, created an Active
50% Administrator allocation on synthetic project PROJ-0131 for September 14–18.
Calculating that project/date range displayed 0 estimated and 20 available hours.
Created one Approved Holiday leave day for September 16 through Add leave.
Recalculation displayed 0 estimated and 16 available hours, matching four
8-hour weekdays at 50%. Both creation dialogs confirmed save and closed.
These retained synthetic QA records verify allocation/leave creation and capacity
rendering for Administrator. Restricted-role access and over-capacity rendering
are not established by this particular scenario.

## Commercial links acceptance — 2026-09-16

In Chrome on the isolated QA site, opened Business details for synthetic project
`PROJ-0131` (Commercial browser acceptance), selected customer
`Pulse commercial 5beb07c0` and its draft order `SAL-ORD-2026-00001`, and saved.
The project row displayed both links. Reloading and reopening Business details
retained both selected values. Changing the customer to the other synthetic
customer immediately cleared the selected order; after loading, the order list
contained only No sales order. Cancel preserved the previously saved links.
This verifies the Administrator UI selection/filter/save/reload path, not
restricted-role access or submission of a commercial transaction.

Environment: isolated `pulse-qa.localhost` Frappe/ERPNext bench, HTTP port 18016, Chrome controlled through the CUA browser tools. Synthetic test data only. This record distinguishes observed behavior from planned checks; API tests do not establish browser acceptance.

## 2026-09-16 initial access

1. Navigated to `http://pulse-qa.localhost:18016/pulse` in a dedicated Chrome tab.
2. The browser redirected to `/login?redirect-to=/pulse` and displayed **Internal Server Error**.
3. After the runtime adopted a fixed-site loopback wrapper, navigated to `http://127.0.0.1:18016/pulse`.
4. The browser again redirected to `/login?redirect-to=/pulse`, displaying **500 Internal Server Error** and the server error message.

The realtime validation workstream traced this to missing Frappe bundled assets (`jinja_globals.py`, `bundled_assets` was `None`). The runtime workstream was notified to build assets. No credentials were printed or entered into an error page. No browser mutations occurred. No application feature is accepted on this evidence.

## Pending browser scenarios

All scenarios below are **not yet exercised**, pending a functioning login and a migrated, rebuilt application.

| Area | Concrete acceptance scenario |
|---|---|
| Tasks and project configuration | Create a synthetic project; configure status name/color/order and task types; create a task with labels, estimates, start/due dates; save/reopen rich description; inspect field and assignment activity. |
| Bulk tasks and existing relations | Select multiple tasks; edit, assign, move, archive; confirm subtasks, dependencies, checklists and comments remain available. |
| Views | Create calendar, timeline and spreadsheet views; drag a date, resize a timeline bar, edit a cell; apply nested AND/OR filters and grouping; reorder/hide columns; save/reload personal/shared views. |
| Sprints | Move backlog work into a sprint; set goals and workload; change scope and complete work; inspect count/effort history; close with explicit unfinished-work disposition and inspect summary. |
| Intake | Submit and review a request; defer/reject/duplicate/accept; verify accepted task history; exercise configured public form without exposing unrelated project data. |
| Documentation | Create formatted page from a template, link a task, comment and mention, search, inspect revisions; check collaborative edits in two browser sessions when available. |
| Everyday use | Global search, command palette, shortcuts, inbox read/unread, follow, favorites, recent items, quick create, responsive layouts, and visible error recovery. |
| Business and time | Customer/order linkage, template project creation, manual time, timer stop, billable distinction, estimate/actual totals, native timesheet link and workload. |

Source-level and runtime verification are recorded separately in `verification-matrix.md` and runtime reports. Passing checks will be added with the exact interaction, observed result and limitations.

## 2026-09-16 resumed preview and task checks

After the runtime built Frappe/ERPNext assets, the login page rendered correctly. Signed in to the isolated site as Administrator with the locally stored test credential, without printing it. Pulse rendered its Home page and new navigation. Initial Board and Projects POST calls reported `Invalid Request` during concurrent runtime work; reloading after the test window resolved this. The cause of that transient token/session mismatch was not conclusively established by browser evidence.

| Check | Observed result |
|---|---|
| Project creation | Created `Browser QA September` through Projects → New project, with notes. Success toast and project card appeared; Open board navigated to `PROJ-0035`. |
| Task creation and estimates | Created `Browser QA task one` (`BQS-1`) through project Board → New task, with description, 3 estimated hours and 5 points. Card appeared in Backlog; drawer confirmed all entered values. |
| Favorite/follow | Favorite and Follow task changed to pressed `★ Favorited` and `Following` buttons. Reopened task retained both states. |
| Manual billable time | Saved 0.5 hours with `Browser QA manual time`. Drawer showed 0.50 visible hours / 3.00 estimated, 0.50 billable / 0.00 nonbillable, draft state and native Timesheet link `TS-2026-00003`. |
| Timer | Start timer showed running state; Stop & save returned to Start timer and added a nonbillable draft native Timesheet link `TS-2026-00004`. Short interval rounds to 0.00h in UI; this does not imply a zero-duration database entry. |
| Comments | Sent `Browser QA comment preserved.` and saw it attributed to Administrator; it remained after reopening. |
| Custom status | Renamed unused `To Do` to `Ready` in Task settings and saved workflow. Board column changed to Ready. No category change was made. |
| Label creation | Added `Browser QA` label; settings showed its name and default `#3b82f6` color. Applying it to tasks and custom-color persistence remain untested. |

Open defect: changing the task drawer Status from Backlog to In Progress changed the local selection but did not move the card or persist on reopening; Activity remained empty. Reported to task UI owner. A transient `Could not load task details` appeared on reopen; its Retry action successfully restored the drawer. Broad feature acceptance remains incomplete.

Runtime tests and browser writes must use separate windows: ERPNext Task nested-set operations can contend even when fixtures have unique names.

## Latest creation and navigation acceptance — 2026-09-16

On the rebuilt real backend preview in Chrome:
- Created `Repeat creation acceptance` as BQS-9 in Browser QA September using the inline list form. The saved task appeared once; the creation input remained enabled for the next entry. Clicking the Work items heading removed the creation form.
- Switched to Timeline and clicked the existing BQS-9 row's September 1 scheduling button. Its bar appeared with a one-day duration and no title input. Existing-row buttons now update start/end dates atomically rather than create a duplicate task; existing duration is preserved when rescheduling.
- Pages reader for QA meeting template 0916 measures 1016px within the 1216px workspace (200px page library), with 24px padding and no max-width cap. Screenshot inspection confirmed the content uses the remaining pane.
- Project selection keeps sidebar order within the current session and expands only the selected project's links. Sprints, Intake and Timesheets links are absent from the sidebar navigation.

Latest frontend build and seven existing frontend tests pass. These checks do not replace remaining mobile, permission, and broader workflow acceptance.

## Timeline interaction and module modal — 2026-09-16

- Replaced timeline bar native HTML drag with pointer movement and live date preview; arrow keys also move a focused bar. Date edits/rescheduling now refresh in the background rather than showing the full loading state.
- In Chrome, dragged BQS-9 two days right: its bar moved from x848 to x932 with no error. Dragged the end handle another two days: saved duration changed from 2d to 4d.
- Add module now uses a native modal dialog with initial name focus, accessible title, Escape/backdrop dismissal, two-column properties, mobile stacking, in-modal save errors, and disabled controls during save.
- Screenshot inspected the modal. Created `Module modal acceptance` through it; the module detail opened and the modal closed. The UI design detector reports no findings and the frontend build passes.

## Fullscreen and footer acceptance — 2026-09-16

- Spreadsheet Add work item measured bottom=639 in a 639px viewport: it is pinned to the bottom of the work area.
- Calendar Options switched to Week layout and displayed September 14–18, 2026; weekday-only range is correct.
- Opened BQS-8 and expanded fullscreen: dialog x=0,y=0,width=1440,height=639 matched the viewport. Breadcrumb reads Browser QA September / Work items / BQS-8. Module picker loads Module modal acceptance and QA release module without the former API endpoint error.
- Added three actual-handler timeline regression tests for delayed save stability, duplicate-save prevention, resize failure rollback, move failure rollback, and read-only rejection. All 10 frontend tests pass. Date mutation refreshes are deferred during optimistic saves so realtime cannot overwrite the pending position.

## Business workflow follow-up — 2026-09-16

- Temporarily marked Browser QA September as a template through Business details. First browser clone returned Internal Server Error; this failure is retained as an unexplained transient, not attributed to an unproven fix.
- User approved an isolated Administrator diagnostic clone with transaction rollback. It returned a project plus nine task mappings successfully; rollback executed.
- Subsequent browser clone `Browser clone acceptance 2` succeeded, opened its board, and displayed all nine copied tasks in Ready with unassigned state. Source project's template flag was restored through Business details; Templates count returned to two.
- Workload UI scoped to Browser QA September for September 1–30 displayed exactly 3 unassigned estimated hours and no allocation rows. This verifies unassigned/date-scope rendering; allocation/leave capacity calculations retain backend evidence and still need a dedicated browser scenario.
- Fixed audit callers to use native Task.name rather than issue_key for the Dynamic Link. Focused real-backend regression test `test_task_audit_uses_native_record_names` passed (1 test, 0.876s); retained log `../.work/pulse-bench/audit-regression.log`.
# Mention popup acceptance

Chrome, local QA: reproduced missing suggestions in the collaborative meeting
page editor. TipTap starts its suggestion renderer with an empty list; Frappe
UI's conditional list root prevented popup attachment. The narrowly scoped Vite
resolver now supplies Pulse's stable-root mention list, without changing installed
dependency files or other suggestion types.

Rebuilt production assets, typed `@Adm`, observed the Administrator option,
selected with Enter, closed the editor (flushing shared changes), and reloaded
the page. The rendered mention retained `data-id="Administrator"` and text
`@Administrator`. This proves suggestion, keyboard selection, shared save and
reload for an eligible project member; it does not claim another user's email
delivery. The prior CRM source check also showed the explicit unavailable state
on the QA site where Frappe CRM is not installed.
# Restricted-user browser acceptance

Used a separate Chrome cookie hostname `permissions.localhost:18018`, backed by
the isolated `pulse-qa.localhost` site. Synthetic Senior Developer
`pulse-browser-ed13f2b8@example.test` belongs only to PROJ-0222; PROJ-0223 and its
task are private. The visible task TASK-2026-00107 depends on the hidden
TASK-2026-00106, created by Administrator before the browser check.

- Home/project navigation showed only the permitted project.
- List and Kanban showed the permitted task. Its drawer's Relationships section
  omitted the private dependency, with no private title or ID rendered.
- Global search for the shared fixture suffix returned only the permitted task
  and project, excluding both matching hidden records.
- Direct navigation to the hidden project returned a permission error. A direct
  hidden-task link also returned a permission error without task details.
- The denied-task state exposed only Retry, so a visible Close action was added
  to both loading and error states. The frontend build passed
  (`/tmp/pulse-task-recovery-build.log`). Chrome reload showed Close during
  loading and alongside the permission error; clicking it removed the dialog
  and left the permitted task visible on the board.

This is actual restricted-user Chrome acceptance, complementing backend tests.
It does not certify every role, report/export, or membership-revocation race.
Fixtures are retained in the disposable QA site. The initial port-18017 start
failed because the separate CRM QA server owned that port; no process was killed
and the permission server was started on 18018 instead.

# Bulk assignment follow-up

In Chrome on the isolated QA site, Administrator selected both CBA-1 and CBA-2
in PROJ-0131 using Select visible tasks, selected the existing synthetic user
`pulse-rt-member-mu4c43m9@example.com`, and applied the bulk change. Both cards
showed one assigned user. A full browser reload retained both assignments.
Opening CBA-1 and Activity & comments showed the assignment event with
Administrator and its timestamp. Existing status, priority and Milestone type
were retained. These are retained synthetic fixtures; this does not establish
restricted-assignee access or external notification delivery.
