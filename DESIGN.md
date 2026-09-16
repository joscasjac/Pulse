# Pulse design system

## Direction
Plane-inspired operational workspace. User-selected reference: https://github.com/makeplane/plane and the product interface shown at https://plane.so/ (inspected 2026-09-16). Preserve Pulse identity and native ERPNext behavior.

## Composition
Desktop: 224px quiet sidebar, 48px contextual top bar, white content canvas. Sidebar prioritizes Home, Inbox, My work, then Projects, Views, Pages and Timesheets. Project selection reveals Tasks, Sprints, Intake and Pages in context. Advanced planning, reporting and administration are grouped under More/Settings rather than a long flat list. All prior routes remain accessible.

## Visual grammar
Light is the initial theme for daytime team work; preserve explicit saved dark preference. Neutral white canvas, near-white sidebar, subtle gray dividers, readable charcoal text, restrained blue action accent. No decorative gradients, oversized metric tiles or dashboard marketing copy. Compact typography and information density, generous separation between groups. Status color has semantic purpose.

## Tokens
Body system sans stack, 13px navigation, 14px body, 20–24px page titles with medium/semibold weight. Controls 32px high, 6px radius; surfaces flat with 1px borders, 8px cards only when grouping real entities. Accent #3b5bdb, on-accent white; text #202124, muted #60646c; canvas #ffffff, sidebar #f7f8fa; border #e6e8ec. Dark equivalents retain sufficient contrast.

## Interaction
One prominent creation action per context. Filter and display controls grouped in a consistent toolbar. Task properties live in a clean drawer; details and activity have clear separation. Defaults keep advanced configuration collapsed. Keyboard focus visible; controls have accessible labels; menu and drawer Escape behavior and mobile overlays preserved. Tables and boards scroll within their content region.

## Responsive
Sidebar becomes a drawer below768px; compact header remains. Toolbars wrap without hiding actions. Dense data tables use horizontal scroll; forms become one column. No page-wide overflow.

## Validation
Inspect real rendered desktop/mobile pages after build. Functional acceptance against the real backend must continue after the redesign. No feature may be removed to simplify appearance.

## Density refinement from user review
The user rejected the first pass as bloated. Task workspaces must expose List, Board, Calendar, Timeline and Spreadsheet together in one compact toolbar. Filters and display options stay closed by default. Bulk actions appear only after selection. Avoid repeating a project selector when the project is already established in the breadcrumb. Inactive layout icons use explicit readable neutral color; active state uses a subtle neutral background and darker icon, never white on light gray. Task detail emphasizes title, status/priority/assignee and description; other properties, time, relations and attachments use compact disclosure sections. Pages uses one compact library toolbar and a readable content area with secondary metadata tucked away.

## Pane and interaction refinement
Split workspaces fill the available viewport and keep their headers fixed. Lists and selected detail panes scroll independently; nested task lanes have their own scroll areas. Calendar, timeline and spreadsheet occupy the working pane without an always-visible duplicate date form. Shared checkboxes use compact rounded outlines and a clear checked/focus state. Drag grips provide mouse/touch movement; insertion markers show the exact card or row destination.

## Calendar reference supplied by user
Match the supplied Plane calendar screenshots: month arrows and prominent month/year at left; Today and Options at right; weekday headers and roomy date cells, weekday-only default with optional weekends; date numbers at upper right and current day circled. Each date exposes an Add task menu on hover/keyboard focus with create-new and add-existing actions. Existing-task selection is a searchable multi-select dialog with status dots, identifiers, titles, selected count, Select all, Cancel and explicit Add selected action. Compact cards show identifier and title, open task details, and drag to reschedule with duration preserved. Date-targeted creation must prefill due date. Persist options with the user's project-specific view preferences.
