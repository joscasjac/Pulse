# Optional Frappe CRM tasks

Frappe CRM's native `CRM Task` remains authoritative. Pulse does not create ERPNext Task copies, maintain a sync table, or mutate CRM's schema. My work combines independently loaded sources, qualified identity `frappe_crm:CRM Task:<name>`, and Source filters (All work / Project tasks / CRM tasks). A source outage does not discard the other source's successful result. Returning focus refreshes source changes.

CRM tasks assigned to the current user appear with native priority/status, due date, and permission-checked Lead/Deal links. Inline editing saves title, status (including Done), priority, start date and due date on the original CRM Task. Optimistic concurrency rejects stale edits. Read-only tasks have no edit form. Lists require native task list/document permission plus parent Lead/Deal read permission; writes require task read/write and parent read permission. Unknown or incomplete references fail closed.

Absent `crm` app or `CRM Task` DocType returns an explicit unavailable response. The original Pulse QA bench lacks Frappe CRM. The isolated official-CRM backend run below validates source edits and restricted sales users; combined-app backend and installed-CRM Chrome evidence are recorded below. Six isolated adapter tests cover optional absence, parent denial, identity/URL, source-only writes, parent write denial, and stale writes. Vue SFC compilation and UI detector passed. These adapter tests complement the six real CRM backend tests recorded below; they do not claim browser acceptance.

Schema reference inspected 2026-09-16: https://raw.githubusercontent.com/frappe/crm/v1.84.0/crm/fcrm/doctype/crm_task/crm_task.json and companion controller. Upstream due_date is Datetime; start_date is Date. CRM Task statuses stay native rather than being rewritten to project workflow states.

## Remaining explicit project association

CRM tasks intentionally do not appear on project boards yet. No implicit association is inferred from a lead/deal/customer. To support user-selected project membership without duplication:

- Add a small Pulse CRM project membership DocType referencing CRM Task + native Project, unique per pair. Require source task write and project write for link/unlink; native source data remains untouched.
- Board and Views loaders need a discriminated record adapter (native Task vs CRM Task) and permission checks on both sources plus project; source-specific editor/status/date mutation handlers must avoid sending CRM IDs to native `tasks.move_task`, task drawer or bulk-edit APIs.
- Define board lane mapping between each project's configured category and native CRM statuses, with explicit missing mapping handling; native CRM has no project rank field, so ordering metadata belongs on the association only.
- Extend filtering, selection/bulk updates, realtime invalidation, calendar/timeline and module scope consciously rather than treating CRM rows as partially populated ERPNext Tasks.

No project-membership support is claimed by this initial integration.

## Runtime feasibility (read-only inspection)

Official stable `main` currently reports CRM 1.84.0; pyproject accepts Python >=3.10 and Frappe >=15,<17. The existing Frappe 16.34 bench meets that declared framework constraint. The stable task schema matches the adapter. Official frontend routes confirm `/crm/leads/:leadId` and `/crm/deals/:dealId`. This initial read-only assessment was followed by the isolated installation recorded below.

Recommended isolated validation: fetch stable CRM with bench get-app (pin verified main commit/tag), create a separate `crm-qa.localhost` database/site using the existing isolated DB/Redis services, and install ERPNext, Pulse and CRM on that site. Build CRM assets only for actual browser acceptance. Shared bench Python package changes remain possible; a separate bench is stronger isolation if those changes conflict. Never run CRM install/migrate against the current Pulse QA site without coordinating root. Subsequent `git ls-remote` verified the v1.84.0 tag and exact commit recorded below.

## Real CRM backend acceptance — 2026-09-16

Official stable tag `v1.84.0` was verified and cloned at `0adc6715d79b7647d1bcecf41f5d2cf928253b4b` into `.work/pulse-crm-qa/crm`. A separate bench/site/database `crm-qa.localhost` / `pulse_crm_qa` was created, with shared framework source and read-only Python environment. Twilio dependencies were installed into the private QA `vendor` directory only. No CRM installation/migration was performed against `pulse-qa.localhost`, its server was not restarted, and its apps registry was not changed.

Official CRM installed successfully. Six real backend tests passed in 1.248 seconds: assigned list includes accessible parent and excludes restricted parent; title/date/status completion updates the original CRM Task; restricted parent edit rejected; stale modified edit rejected; Guest write rejected; reversed dates rejected. Tests used actual Sales User roles, CRM Lead ownership permission hooks, and the actual CRM Task controller. Source edit remained visible through fresh native reads. Fixtures are confined to the separate CRM QA database. Reusable conditional integration coverage is in `pulse/tests/test_crm_tasks_integration.py`; sites without CRM explicitly skip it.

Evidence: `.work/pulse-crm-qa/validation.log`, installation logs and runner. At this initial checkpoint, browser editing, combined-app hooks, and project association were not covered. The combined-app backend run below closes the hook-validation gap, but not browser editing or project association.

## Combined installed-app acceptance — 2026-09-16

ERPNext and Pulse were installed successfully alongside CRM on the **separate** `crm-qa.localhost` site. The isolated `install-combined.py` enters only `.work/pulse-crm-qa/bench/sites`, initializes `crm-qa.localhost`, then calls Frappe's `install_app('erpnext')` and `install_app('pulse')`. It uses the existing environment and private CRM vendor path; no pip/dependency change to the shared environment occurred.

Commands from the Quotes workspace:

```sh
.work/pulse-bench/bench/env/bin/python .work/pulse-crm-qa/install-combined.py > .work/pulse-crm-qa/install-combined.log 2>&1
.work/pulse-bench/bench/env/bin/python .work/pulse-crm-qa/run-repo-tests.py > .work/pulse-crm-qa/combined-validation.log 2>&1
```

Both exited 0. All six reusable CRM integration cases passed in **1.068 seconds** with the actual CRM, ERPNext and Pulse hooks installed. The completion test now also compares native ERPNext Task counts before and after, confirming no duplicate Task was created. Fixtures create real CRM Leads/Tasks and ToDo assignments through native controllers; test mutations are rolled back.

This run covers backend operations. The subsequent Chrome section covers the installed-CRM editor; explicit project-board membership remains unimplemented. The original Pulse QA site/server/installed-app registry were untouched.

## Installed-CRM Chrome acceptance — 2026-09-16

Started a separate loopback-only Werkzeug server on port 18017 using `.work/pulse-crm-qa/qa-http.py`, fixed to `crm-qa.localhost`. Chrome used `http://localhost:18017` so cookies were separate from the existing Pulse QA host `127.0.0.1`. Existing Pulse server/session was not touched. A synthetic Sales User + Pulse Manager account and CRM Lead/Task were created only on the isolated site; login credentials are local test-only and omitted here.

Through CUA Chrome UI, My work loaded native **CRM-7**, “CRM browser follow-up,” Todo/Medium, linked to **CRM-LEAD-2026-00003**. Opened the inline editor and changed title to “CRM browser edited follow-up,” status to **Done**, priority **High**, start date **2026-09-16**, due date/time **2026-09-18 15:30**. Save succeeded: the Open count fell to zero and Completed became one. Completed view displayed the edited title/High/Done/18 Sept. Reloaded the actual page, selected Completed + CRM tasks, reopened the editor, and verified every saved field including the date/time persisted. A screenshot inspection confirmed the compact neutral form fits the desktop pane and retains accessible labels. Selecting Project tasks excluded the CRM record and showed zero completed project tasks.

Browser tab 1904375397 was agent-created for this test. Source linkage URL was rendered correctly; the CRM app's own Lead page was not opened because this isolated install does not build CRM frontend assets. The tested UI is Pulse's real built frontend against the installed combined-app backend, not mocked browser data. Explicit project-board association remains unimplemented; general mobile and parent-permission browser testing are not claimed here (parent permissions were tested on the real backend above).
