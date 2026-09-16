"""Native time integration tests; run on an isolated ERPNext test site."""
import frappe
from frappe.tests import IntegrationTestCase


class TestNativeTime(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.project = frappe.get_doc({"doctype": "Project", "project_name": "Pulse time " + frappe.generate_hash(length=10)}).insert()
        from pulse.api.spa import create_task
        self.task = create_task(self.project.name, "Timed delivery")["name"]

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("Pulse Timer", "Administrator"):
            frappe.delete_doc("Pulse Timer", "Administrator")
        for name in frappe.get_all("Timesheet", filters={"owner": "Administrator"}, pluck="name"):
            doc = frappe.get_doc("Timesheet", name)
            if any(row.task == self.task for row in doc.time_logs):
                frappe.delete_doc("Timesheet", name, force=True)
        from pulse.api.spa import delete_task
        delete_task(self.task)
        frappe.delete_doc("Project", self.project.name, force=True)

    def test_timer_stops_into_native_timesheet_once(self):
        from unittest.mock import patch
        from datetime import datetime, timedelta
        from pulse.api.time import start_timer, stop_timer, get_timer
        start = datetime(2024, 1, 3, 9)
        with patch("pulse.api.time.now_datetime", return_value=start), patch("pulse.pulse.doctype.pulse_timer.pulse_timer.now_datetime", return_value=start):
            start_timer(self.task, billable=0)
        with patch("pulse.api.time.now_datetime", return_value=start + timedelta(hours=1)):
            result = stop_timer("Timer work")
        self.assertEqual(result["logged"], 1)
        self.assertIsNone(get_timer())
        with self.assertRaises(frappe.ValidationError):
            stop_timer()

    def test_native_entry_and_billable_summary(self):
        from pulse.api.time import log_time, get_time_summary
        result = log_time(self.task, 1.5, from_time="2024-01-01 09:00:00", billable=1)
        doc = frappe.get_doc("Timesheet", result["timesheet"])
        self.assertEqual(doc.user, "Administrator")
        self.assertEqual(doc.docstatus, 0)
        self.assertEqual(doc.time_logs[0].task, self.task)
        self.assertEqual(doc.time_logs[0].hours, 1.5)
        summary = get_time_summary(self.task)
        self.assertEqual(summary["actual_hours"], 1.5)
        self.assertEqual(summary["billable_hours"], 1.5)
        self.assertEqual(summary["nonbillable_hours"], 0)

    def test_reject_impersonation_and_nonfinite_hours(self):
        from pulse.api.time import log_time
        with self.assertRaises(frappe.PermissionError):
            log_time(self.task, 1, user="another@example.com")
        for hours in (0, -1, "nan", "inf", 25):
            with self.assertRaises(frappe.ValidationError):
                log_time(self.task, hours)

    def test_deletion_preserves_recorded_time(self):
        from pulse.api.time import log_time
        from pulse.api.spa import delete_task
        record = log_time(self.task, 1, from_time="2024-01-02 09:00:00")
        with self.assertRaises(frappe.ValidationError):
            delete_task(self.task)
        self.assertTrue(frappe.db.exists("Timesheet", record["timesheet"]))
        self.assertTrue(frappe.db.exists("Task", self.task))

    def test_timer_timestamp_is_server_owned_and_running_fields_immutable(self):
        from pulse.api.time import start_timer
        from frappe.utils import now_datetime, get_datetime
        timer = frappe.get_doc({"doctype": "Pulse Timer", "user": "Administrator",
                                "task": self.task, "started_at": "2000-01-01 00:00:00"}).insert()
        self.assertLess(abs((now_datetime() - get_datetime(timer.started_at)).total_seconds()), 10)
        timer.started_at = "2000-01-01 00:00:00"
        with self.assertRaises(frappe.ValidationError):
            timer.save()
        with self.assertRaises(frappe.ValidationError):
            start_timer(self.task)

    def test_zero_and_long_timer_preserve_recoverable_state(self):
        from datetime import datetime, timedelta
        from unittest.mock import patch
        from pulse.api.time import start_timer, stop_timer, discard_timer
        start = datetime(2024, 1, 4, 9)
        with patch("pulse.pulse.doctype.pulse_timer.pulse_timer.now_datetime", return_value=start):
            start_timer(self.task)
        for end in (start, start + timedelta(hours=25)):
            with patch("pulse.api.time.now_datetime", return_value=end):
                with self.assertRaises(frappe.ValidationError):
                    stop_timer()
            self.assertTrue(frappe.db.exists("Pulse Timer", "Administrator"))
        discard_timer()
        self.assertFalse(frappe.db.exists("Pulse Timer", "Administrator"))

    def test_revoked_task_timer_can_be_discarded_without_exposing_task(self):
        from unittest.mock import patch
        from pulse.api.time import start_timer, get_timer, discard_timer
        start_timer(self.task)
        native_permission = frappe.has_permission
        def permissions(doctype, *args, **kwargs):
            return False if doctype == "Task" else native_permission(doctype, *args, **kwargs)
        with patch("frappe.has_permission", side_effect=permissions):
            timer = get_timer()
            self.assertTrue(timer["restricted"])
            self.assertNotIn("task", timer)
            discard_timer()

    def test_summary_labels_drafts_and_native_general_work(self):
        from pulse.api.time import log_time, get_time_summary, get_my_time
        result = log_time(self.task, 2, from_time="2024-02-01 09:00:00")
        summary = get_time_summary(self.task)
        self.assertEqual(summary["draft_hours"], 2)
        self.assertEqual(summary["submitted_hours"], 0)
        self.assertEqual(summary["scope"], "permitted_timesheets")
        self.assertIn(result["timesheet"], [r["timesheet"] for r in get_my_time()["entries"]])

    def test_migration_dry_run_idempotence_and_partial_retry(self):
        from pulse.services.time_migration import migrate
        from frappe.utils import get_datetime
        old = frappe.get_doc({"doctype": "Pulse Timesheet", "user": "Administrator",
                              "week_starting": "2023-05-01", "entries": [
                                  {"task": self.task, "date": "2023-05-01", "hours": 1},
                                  {"task": self.task, "date": "2023-05-01", "hours": 2}]}).insert(ignore_permissions=True)
        try:
            migrate(dry_run=True)
            self.assertFalse(frappe.db.exists("Timesheet Detail", {"pulse_legacy_entry": old.entries[0].name}))
            migrate(dry_run=False)
            first = frappe.db.get_value("Timesheet Detail", {"pulse_legacy_entry": old.entries[0].name}, "parent")
            native = frappe.get_doc("Timesheet", first)
            self.assertEqual(native.docstatus, 0)
            # Simulate an earlier partial migration that retained only the first row.
            native.remove(native.time_logs[1])
            native.save()
            migrate(dry_run=False)
            second = frappe.db.get_value("Timesheet Detail", {"pulse_legacy_entry": old.entries[1].name}, ["parent", "from_time"], as_dict=True)
            self.assertEqual(get_datetime(second.from_time), get_datetime("2023-05-01 01:00:00"))
            retry = migrate(dry_run=False)
            self.assertIn(old.entries[0].name, retry["already_migrated"])
            self.assertIn(old.entries[1].name, retry["already_migrated"])
            self.assertTrue(frappe.db.exists("Pulse Timesheet", old.name))
        finally:
            # Remove only this fixture's native copies, retaining production provenance.
            for name in frappe.get_all("Timesheet", filters={"pulse_legacy_timesheet": old.name}, pluck="name"):
                frappe.delete_doc("Timesheet", name, force=True)
            frappe.delete_doc("Pulse Timesheet", old.name, ignore_permissions=True, force=True)

    def test_migration_retains_non_task_work(self):
        from pulse.services.time_migration import migrate
        from pulse.api.time import get_my_time
        old = frappe.get_doc({"doctype": "Pulse Timesheet", "user": "Administrator",
                              "week_starting": "2023-06-01", "entries": [
                                  {"date": "2023-06-01", "hours": 1.25, "billable": 0,
                                   "activity_type": "Other", "description": "General planning"}]}).insert(ignore_permissions=True)
        try:
            migrate(dry_run=False)
            row = frappe.db.get_value("Timesheet Detail", {"pulse_legacy_entry": old.entries[0].name},
                                      ["parent", "hours", "task", "description"], as_dict=True)
            self.assertEqual(row.hours, 1.25)
            self.assertFalse(row.task)
            self.assertIn("General planning", row.description)
            self.assertIn(row.parent, [entry["timesheet"] for entry in get_my_time()["entries"]])
        finally:
            for name in frappe.get_all("Timesheet", filters={"pulse_legacy_timesheet": old.name}, pluck="name"):
                frappe.delete_doc("Timesheet", name, force=True)
            frappe.delete_doc("Pulse Timesheet", old.name, ignore_permissions=True, force=True)

    def test_direct_timer_insert_cannot_impersonate(self):
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc({"doctype": "Pulse Timer", "user": "Guest", "task": self.task,
                            "started_at": "2024-01-01 09:00:00"}).insert(ignore_permissions=True)
