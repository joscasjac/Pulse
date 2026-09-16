# Views browser validation

2026-09-16, isolated local QA site at `http://127.0.0.1:18016/pulse`, authenticated Administrator, Chrome through CUA only.

## Observed working

- Work views loads a cross-project spreadsheet with editable native tasks.
- Filters and columns opens with nested AND/OR controls and column visibility/order controls.
- A Title contains `Views QA` rule applied successfully and reduced the spreadsheet to the dedicated fixture.
- Created dedicated `BQS-2` (`Views QA calendar alpha`) through the scoped Board create dialog in `PROJ-0035`.
- Changed its title inline to `Views QA calendar alpha edited`; UI returned `Task updated.` and replaced the row with the saved title.

## Findings and limitations

- Global New task opened from Work views had an empty Project selector after loading. Scoped Board creation offered the project list and worked. Reported to browser acceptance owner; global creation requires retest/fix.
- Native date entry via CUA `setValue` and locator `fill` did not produce confirmed persisted values. Do not count this as a product defect until input behavior and interrupted browser state are resolved.
- Dedicated tab `1904375179` unexpectedly navigated to Meetings during validation, although this agent issued no Meetings navigation. Reported to root for browser coordination; subsequent date evidence is invalidated.
- Runtime owner requested mutation pause while addressing Task nested-set deadlocks.

## Still unverified

Calendar drag-reschedule, Gantt resize and dependency links, date edits, all grouping modes, nested AND/OR result semantics, saved personal/shared views, column persistence and reload preferences. These are not signed off by this limited pass. A requested Plane-inspired redesign is in progress; no visual acceptance is implied.

## September 16 continuation: real scheduling gestures
Root authenticated Administrator in project PROJ-0035 against live Frappe/ERPNext:
- Calendar dragged BQS-2 from Sept18 to Sept19. Calendar moved the event and Edit dates showed start Sept17/due Sept19 (original Sept16/18), preserving two-day duration.
- Timeline dragged end handle +34px: due changed Sept19→20 and success state displayed. Dragged start handle -34px: start changed Sept17→16. Both changes returned from real API reload, not local mock state.
- Existing gaps: dependency creation/line rendering and denied-user UI recovery still require browser coverage; layout persistence reset was found and is being repaired.

## Plane calendar reference acceptance
- Weekday-only calendar rendered with date add menus, Today and Options.
- Sept16 Add existing tasks opened searchable picker; searching BQS-2 returned only that task. Selected and submitted: dialog closed, 'Tasks scheduled.' displayed, BQS-2 rendered on Sept16.
- Sept17 Create task opened project-prefilled modal with due Sept17. Created 'Calendar reference acceptance' as BQS-3; it appeared on Sept17 with native creation success toast.

## Inline creation acceptance

Real Administrator browser on PROJ-0035: Gantt date + on September18 opened inline title editor, Enter created BQS-5 `Gantt inline QA` with start/due2026-09-18, visibly rendered1-day bar immediately and reset/refocused title input. Spreadsheet footer + Add task opened inline editor; Enter created `Spreadsheet inline QA` and real editable row appeared. Found Gantt editor clipping at right/bottom edge; handed to timeline owner for positioning fix.

List follow-up: group Ready header + opened inline editor; Enter saved `List inline QA` and its status control appeared in Ready. Escape closed editor. Follow-up positioning build succeeded (/tmp/pulse-inline-position-build.log); clipping correction still awaits rendered retest.

Positioning retest: latest built timeline editor on Sep18 fully visible inside pane including title, submit/cancel and hint after automatic pane scroll. No workspace scroll observed.

Saved view and grouping acceptance: created personal `QA inline work` with Title contains `inline QA` filter,3matching tasks in Spreadsheet. Reloaded and selected saved view; Spreadsheet and one filter restored with3matching tasks. Switched to Timeline, selected Display→Group by Status; screenshot showed Backlog2 and Ready1 headers within the shared date grid, with bar aligned in correct group. Grouped timeline build passed.

## Saved views and table preferences acceptance — 2026-09-16, redesigned UI

Actual Chrome tab `1904375277`, isolated from user preview and root sprint tabs; real authenticated local backend. No task records changed in this pass.

Verified through UI:

- Nested filter `Title contains "inline QA" AND (Title contains "Spreadsheet" OR Title contains "Gantt")` returned exactly `Spreadsheet inline QA` (BQS-6) and `Gantt inline QA` (BQS-5), excluding `List inline QA`.
- Changing that nested OR to AND returned the visible `No matching tasks` empty state. Reopening the saved view restored the OR result set of two rows.
- Display search `Created` narrowed the column picker to Created date and Created by.
- Hid Project, moved Priority earlier than Status, and enabled Created date. Actual table headers became `Task, Priority, Status, Start date, Due date, Created date`.
- Browser reload preserved that header sequence, visibility, nested filter result and Spreadsheet layout.
- Created personal saved view `QA nested personal 1918`; observed `View saved.` and selectable entry.
- Reopened that personal view, created shared copy `QA nested shared 1918`; observed `View saved.` and `QA nested shared 1918 · Shared` selector entry.
- Switching between personal and shared saved entries restored their saved filter semantics and two matching task rows.

No source defect found in this pass. Sharing was verified as the Administrator creator; cross-user visibility and edit restrictions remain covered by separate backend permission tests, not this browser pass. QA saved views were retained for review. The earlier limited pass does not supersede these newer filter/column/saved-view results.
