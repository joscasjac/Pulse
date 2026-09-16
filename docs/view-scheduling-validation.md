# Calendar scheduling and view preference validation

Focused tests against isolated `pulse-qa.localhost` on 2026-09-16, with an exclusive database window:

- `bench --site pulse-qa.localhost run-tests --app pulse --module pulse.tests.test_views`: 3 integration tests passed in 1.098 seconds.
- `bench --site pulse-qa.localhost run-tests --app pulse --module pulse.tests.test_view_scheduling`: 4 integration tests passed in 1.032 seconds.

The tests exercise native Frappe documents and permissions. They verify private/shared view ownership, direct-document owner spoof denial, user/project/editor preference isolation, retained ordering and weekend settings, multi-task date scheduling with duration preservation, all-task permission checks before updates, and rollback of earlier writes when a later task fails native validation. Invalid dates and selections over 200 tasks are rejected.

The scheduling endpoint sets the selected due day, preserving any existing start-to-due duration; tasks without a start date keep no start date. Backend tests do not establish browser gesture or picker usability. Root owns browser acceptance after worker reload.
