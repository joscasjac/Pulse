# Real HTTP and realtime privacy smoke

Run only against an isolated, disposable Frappe 16 + ERPNext 16 site with Pulse installed and migrated. The script creates uniquely named users, a project, a task and a page. It exercises the actual HTTP upload/download and API endpoints and actual Socket.IO transport; it does not mock realtime publishing.

Install frontend dependencies first (the script resolves its Socket.IO client there). Start the site's HTTP service and Socket.IO service. Socket.IO must be able to reach HTTP using its Origin hostname and resolve that request to the same site.

```sh
PULSE_ADMIN_PASSWORD_FILE=/absolute/path/to/mode-0600-password-file \
  node scripts/qa/realtime-smoke.mjs
```

Defaults: HTTP `http://127.0.0.1:18016`, Socket.IO `http://127.0.0.1:19016`, site `pulse-qa.localhost`. Override with `PULSE_HTTP_URL`, `PULSE_SOCKET_URL`, `PULSE_SITE`. Credentials and session cookies stay in memory and are never printed.

Checks include member/outsider socket connections, comments, follower notifications and recipient-only delivery, inbox updates, native multipart uploads, mandatory file privacy, authorized downloads and unauthorized read/delete attempts, initial document-room subscription authorization, and private file access after the uploader loses project membership.

Cleanup is best effort through normal HTTP APIs; link-protected rows are reported explicitly as `CLEANUP pending`. The disposable site owner must remove those fixtures before reuse. A failed assertion is not a successful acceptance run.
