# Browser documentation and intake validation

## Reject and duplicate decisions follow-up

Chrome Administrator, isolated PROJ-0131: created `Intake rejected browser QA`
(`5ug5dscl7v`), saved Rejected with a rationale, and reopened Rejected queue.
Description and original Created event remained alongside Reviewed/Rejected,
note, actor and timestamp. Created `Intake duplicate browser QA` (`690v4970gh`),
saved Duplicate referencing the first request with a note, and reopened Duplicate
queue. Full reload retained the duplicate decision, original-request reference,
description, Created event and Reviewed event. Neither displayed an accepted-task
link. QA fixtures retained. Intake remains hidden from navigation as requested;
these checks used its existing direct route. Combined with prior accept, defer,
reviewer, guest submission and disabled-form checks, all named decision paths now
have Administrator browser evidence; restricted reviewer access remains bounded
by separate permission tests.

Date: 2026-09-16. Actual Chrome browser through CUA, isolated local Frappe/ERPNext at `http://127.0.0.1:18016`. Administrator session. This is partial evidence, not overall acceptance.

## Verified through the browser

- Opened Documents through the sidebar (`/pulse/documents`).
- Created `Browser Docs QA 0916` under `Browser QA September` (`PROJ-0035`) using the Project brief template.
- Template populated rich headings and sections: Project brief, Outcome, Scope, Stakeholders, Milestones.
- Selected `Browser QA task one` (`TASK-2026-00016`) in Linked tasks and clicked Create page.
- Observed `Page saved.`, the page listed in Project pages, rendered heading hierarchy and template text, and Linked work hyperlink to the correct native task.
- Opened Edit page and observed `Shared page · changes save automatically`, existing template content, and preserved selected task.
- Opened a second browser tab and observed the saved page in its page list, proving the initial page persisted across tabs.

## Attempted, not yet verified

- Entered `Browser documentation discussion 0916` and clicked Post comment. Immediately opened Edit page; discussion persistence has not been independently checked.
- Opened a second tab for collaboration, but did not edit from it before browser work was paused to avoid contention with root's UI redesign research.

## Remaining browser acceptance

- Two-tab concurrent edits, merge and reload persistence; code blocks, mentions and rich inline formatting.
- Discussion persistence, mention behavior, revision history and restore behavior if exposed.
- Document search by title and body, and meeting/specification templates.
- Intake submit/reviewer assignment, defer/reject/duplicate, acceptance preserving history and native task navigation.
- Public form creation and guest submission in a separate unauthenticated context; invalid input, disabled form and error states.
- Read-only/restricted-user checks and responsive layouts.

## Fixtures and tabs

Dedicated session: `🧪 Pulse docs intake`. Tabs at pause: `1904375182` (first editor), `1904375185` (second list). No existing user documents or tasks were edited. The unique documentation fixture remains in the isolated QA database.

## Follow-up real browser acceptance — 2026-09-16

Administrator, desktop preview on isolated real Frappe backend: created `QA intake acceptance` in PROJ-0035 with description, observed Incoming queue and Created activity, entered review note and accepted. UI switched to Accepted and linked native TASK-2026-00032 (BQS-4). Activity retained Created plus Accepted with review note. Public guest form and other review dispositions remain separate acceptance checks.

## Rich collaborative edit follow-up

Opened Browser Docs QA0916 editor, observed shared editor ready, inserted paragraph `QA shared editor persistence check.`, observed All shared changes saved. Closing editor initially showed stale old read content; reselecting page fetched and rendered saved paragraph, proving backend persistence. Assigned immediate-close refresh defect to documents owner. Second-tab creation timed out in browser automation; no two-browser concurrent editing pass claimed.

Close-refresh fix retest: edited existing shared page with `Immediate close QA.`, clicked Close while sync in progress; reader immediately displayed new canonical paragraph. Expanded Revision history and observed five Administrator timestamp entries with View changes disclosures. This supersedes the earlier stale-close defect.

## Two live browser editors — passed

Two independent Chrome tabs with Administrator session opened same existing page editor. Inserted `Editor A QA.` and `Editor B QA.` through actual contenteditable controls in each tab. Both live rendered editors converged to identical content containing both edits. Closed and reloaded second tab, selected page: canonical reader retained both edits. Closed first editor: same content. No conflict/unsaved loss. This complements distinct authenticated-user HTTP convergence/revocation smoke; browser test uses same logged-in user across two clients. Peer tab closed afterward.

## Guest public form and reviewer follow-up — passed

An unauthenticated in-app browser displayed the public form with Login navigation and only public title/instructions. Empty submission focused required Title and displayed validation. Submitted `Public intake browser QA`; guest saw the thank-you confirmation. Administrator Incoming queue showed request `6jal1ch706`, Guest Created activity and no accepted-task link. Assigned Administrator reviewer, deferred with a note, reopened Deferred queue: reviewer, decision, note and original Guest Created event persisted. Disabled the QA form through admin settings; the same guest link then displayed unavailable and no submission fields. Form remains disabled. Database-level request/task separation and token rotation have separate integration coverage.

## Additional independent acceptance after UI redesign

On 2026-09-16, in a newly created Chrome tab `1904375280` (session `🧪 Docs acceptance`):

- Searching title `Browser Docs QA` returned `Browser Docs QA 0916`.
- Searching body-only text `Immediate close QA` retained that matching page. Searching `no-match-docs-0916-xyz` showed All pages 0 and the useful no-results state.
- Opened Comments on the existing page and independently verified persisted text `Browser documentation discussion 0916`, attributed to Administrator.
- Expanded Revision history and observed eight timestamped revision entries with View changes controls. Individual diffs were not inspected in this pass.
- Created and saved `QA meeting template 0916` in PROJ-0035: rendered Meeting notes, Agenda/list, Decisions, and Actions sections.
- Created and saved `QA specification template 0916` in PROJ-0035: rendered Problem, Requirements, Acceptance criteria/list, and Open questions.
- Inserted a code block through the Code toolbar control with `const qaDocs = true;`; saved page rendered the code block with syntax highlighting and language label.

### Findings reported to root

1. Once, clearing a search and immediately clicking New page while the existing document and expanded history were displayed caused the application error boundary: `This page couldn't load`. Reload recovered. New page from a saved meeting page subsequently succeeded, so the exact trigger is not isolated. No application exception appeared in the available captured browser error log (only unrelated extension errors).
2. In the newly saved specification's comment control, typing `@` and then `@Admin` displayed literal text without mention suggestions. Verified via accessibility tree and screenshot. The draft was not posted. Source inspection suggests stale mention array capture: Frappe UI configures the extension once while Documents.vue replaces the array asynchronously. Its extension supports a reactive getter via `toValue`; this is a candidate diagnosis, not a verified fix.

No build or server restart was performed. Root reports two-client collaboration and public intake/defer/disable already passed elsewhere; those flows were intentionally not repeated or independently claimed here.
