"""Email queue contracts; these tests never send external messages."""
import unittest
from unittest.mock import patch

import frappe
from pulse.api import notify


class EmailNotificationTests(unittest.TestCase):
    def test_email_queues_escaped_content_and_task_link(self):
        with patch.object(notify, "email_enabled", return_value=True), patch.object(
            frappe.db, "get_value", return_value=frappe._dict(email="member@example.test", enabled=1)
        ), patch.object(frappe, "sendmail") as send:
            notify._email("member", "Task assigned", '<img src=x> & task\nNext line',
                          click='https://example.test/pulse?task=one&view="two"')
        payload = send.call_args.kwargs
        self.assertEqual(payload["recipients"], ["member@example.test"])
        self.assertFalse(payload["now"])
        self.assertIn("&lt;img src=x&gt; &amp; task<br>Next line", payload["message"])
        self.assertIn("&amp;view=&quot;two&quot;", payload["message"])
        self.assertNotIn("<img", payload["message"])

    def test_disabled_email_and_system_users_do_not_queue(self):
        with patch.object(notify, "email_enabled", return_value=False), patch.object(frappe, "sendmail") as send:
            notify._email("member", "Task", "Message")
            send.assert_not_called()
        with patch.object(notify, "email_enabled", return_value=True), patch.object(frappe, "sendmail") as send:
            for user in (None, "Guest", "Administrator"):
                notify._email(user, "Task", "Message")
            send.assert_not_called()

    def test_queue_failure_is_logged_without_breaking_task_save(self):
        with patch.object(notify, "email_enabled", return_value=True), patch.object(
            frappe.db, "get_value", return_value=frappe._dict(email="member@example.test", enabled=1)
        ), patch.object(frappe, "sendmail", side_effect=RuntimeError("No outgoing account")), patch.object(
            frappe, "log_error"
        ) as log, patch.object(frappe, "get_traceback", return_value="queue failure"):
            notify._email("member", "Task", "Message")
            log.assert_called_once_with(title="Pulse email notify failed", message="queue failure")

    def test_disabled_missing_or_addressless_users_do_not_receive_email(self):
        for account in (None, frappe._dict(email="former@example.test", enabled=0),
                        frappe._dict(email=None, enabled=1)):
            with self.subTest(account=account), patch.object(
                notify, "email_enabled", return_value=True
            ), patch.object(frappe.db, "get_value", return_value=account), patch.object(
                frappe, "sendmail"
            ) as send:
                notify._email("former@example.test", "Task completed", "Private task details")
                send.assert_not_called()
