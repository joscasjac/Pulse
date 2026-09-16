# Real HTTP and realtime validation

Executed on the isolated `pulse-qa.localhost` Frappe 16 / ERPNext 16 site using `scripts/qa/realtime-smoke.mjs`. Latest run exited **0** on 2026-09-16 after the File download and document notification fixes.

Verified through actual HTTP requests and authenticated Socket.IO clients:

- Native comments create a follower inbox entry and notify only the authorized recipient.
- Read/unread updates and comment mutations reject the unrelated user.
- Native multipart private upload and authorized download work.
- Guest/unrelated users cannot download or delete the private attachment.
- Public upload of an attachment to protected work is rejected.
- Authorized document readers receive updates; an unrelated room subscriber does not.
- Removing membership stops document update metadata delivery, including existing subscribers.
- The original uploader cannot list or download the attachment after membership is removed.

The run used unique test fixtures and cleanup through normal APIs. It did not use production data. This validates transport and access boundaries, not visual UI behavior, concurrent CRDT editing, or load capacity. See the browser and runtime validation documents for those separate checks.
