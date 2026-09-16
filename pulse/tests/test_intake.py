"""Intake lifecycle and native-task conversion on a real ERPNext test site."""
import frappe
from frappe.tests import IntegrationTestCase


class TestIntake(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.test_users = []
        self.project = frappe.get_doc({"doctype": "Project", "project_name": "Pulse intake test"}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        for name in frappe.get_all("Pulse Request Form", filters={"project": self.project.name}, pluck="name"):
            frappe.delete_doc("Pulse Request Form", name, force=True, ignore_permissions=True)
        for name in frappe.get_all("Pulse Request", filters={"project": self.project.name}, pluck="name"):
            frappe.delete_doc("Pulse Request", name, force=True, ignore_permissions=True)
        for name in frappe.get_all("Task", filters={"project": self.project.name}, pluck="name"):
            frappe.delete_doc("Task", name, force=True, ignore_permissions=True)
        frappe.delete_doc("Project", self.project.name, force=True, ignore_permissions=True)
        for user in self.test_users:
            frappe.delete_doc("User", user, force=True, ignore_permissions=True)

    def test_accept_is_idempotent_and_retains_source_history(self):
        from pulse.api.intake import create_request, accept_request, get_request
        request = create_request(self.project.name, "Client request", "Original description")
        first = accept_request(request["name"])
        self.assertEqual(accept_request(request["name"]), first)
        task = frappe.get_doc("Task", first["task"])
        self.assertEqual(task.project, self.project.name)
        self.assertEqual(task.description, "Original description")
        source = get_request(request["name"])
        self.assertEqual(source["status"], "Accepted")
        self.assertEqual(len(source["activity"]), 2)
        self.assertEqual(source["activity"][0]["action"], "Created")
        self.assertEqual(source["accepted_task"], task.name)

    def test_review_and_duplicate_cycle_validation(self):
        from pulse.api.intake import create_request, review_request, accept_request
        a = create_request(self.project.name, "A")["name"]
        b = create_request(self.project.name, "B")["name"]
        review_request(a, "Deferred", note="Revisit next sprint")
        review_request(a, "Duplicate", duplicate_of=b)
        with self.assertRaises(frappe.ValidationError):
            review_request(b, "Duplicate", duplicate_of=a)
        with self.assertRaises(frappe.ValidationError):
            accept_request(a)

    def test_direct_document_cannot_forge_acceptance_or_history(self):
        from pulse.api.intake import create_request
        name = create_request(self.project.name, "Unreviewed")["name"]
        doc = frappe.get_doc("Pulse Request", name)
        doc.status = "Accepted"
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc = frappe.get_doc("Pulse Request", name)
        doc.activity[0].note = "Forged"
        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_review_history_snapshots_reviewer_and_duplicate(self):
        from pulse.api.intake import create_request, review_request
        original = create_request(self.project.name, "Original")["name"]
        name = create_request(self.project.name, "Duplicate")["name"]
        result = review_request(name, "Duplicate", reviewer="Administrator", duplicate_of=original)
        self.assertEqual(result["activity"][-1]["reviewer"], "Administrator")
        self.assertEqual(result["activity"][-1]["duplicate_of"], original)

    def test_public_form_is_revocable_and_exposes_only_public_copy(self):
        from pulse.api.public_intake import save_settings, get_form, submit
        from urllib.parse import parse_qs, urlparse
        settings = save_settings(self.project.name, 1, "Send us an idea", "Describe the outcome")
        key = parse_qs(urlparse(settings["url"]).query)["key"][0]
        frappe.set_user("Guest")
        try:
            self.assertEqual(get_form(key), {"title": "Send us an idea", "description": "Describe the outcome"})
            self.assertEqual(submit(key, "Public idea", "Some details"), {"submitted": True})
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc("Project", self.project.name).check_permission("read")
            with self.assertRaises(frappe.PermissionError):
                save_settings(self.project.name, 0)
            with self.assertRaises(frappe.DoesNotExistError):
                get_form("x" * 43)
        finally:
            frappe.set_user("Administrator")
        rows = frappe.get_all("Pulse Request", filters={"project": self.project.name, "title": "Public idea"}, fields=["name", "status", "owner"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Incoming")
        save_settings(self.project.name, 0)
        with self.assertRaises(frappe.DoesNotExistError):
            submit(key, "After disabling")
        new_settings = save_settings(self.project.name, 1)
        self.assertNotEqual(new_settings["url"], settings["url"])
        with self.assertRaises(frappe.DoesNotExistError):
            get_form(key)

    def test_public_request_rate_limit(self):
        from pulse.api.public_intake import save_settings, submit
        from urllib.parse import parse_qs, urlparse
        from werkzeug.test import EnvironBuilder
        from werkzeug.wrappers import Request
        from unittest.mock import patch
        settings = save_settings(self.project.name, 1)
        key = parse_qs(urlparse(settings["url"]).query)["key"][0]
        # Exercise the actual endpoint decorator with an isolated request/IP counter.
        cache_key = frappe.cache.make_key("rl:pulse.api.public_intake.submit:192.0.2.199") + b":60"
        frappe.cache.delete(cache_key)
        with patch.object(frappe.local, "request", Request(EnvironBuilder(method="POST").get_environ()), create=True), patch.object(frappe.local, "request_ip", "192.0.2.199", create=True), patch.object(frappe.local, "form_dict", frappe._dict(cmd="pulse.api.public_intake.submit"), create=True):
            for i in range(5):
                submit(key, f"Rate limited idea {i}")
            with self.assertRaises(frappe.RateLimitExceededError):
                submit(key, "Too many")
        frappe.cache.delete(cache_key)

    def test_generic_document_write_cannot_bypass_assigned_reviewer(self):
        from pulse.api.intake import create_request, accept_request, get_request
        email = "intake-contributor-" + frappe.generate_hash(length=8) + "@example.com"
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Contributor", "send_welcome_email": 0,
                        "roles": [{"role": "Pulse Senior Developer"}]}).insert()
        self.test_users.append(email)
        self.project.append("users", {"user": email, "welcome_email_sent": 1})
        self.project.save()
        name = create_request(self.project.name, "Protected decision", reviewer="Administrator")["name"]
        frappe.set_user(email)
        try:
            self.assertFalse(get_request(name)["can_review"])
            doc = frappe.get_doc("Pulse Request", name)
            doc.status = "Rejected"
            with self.assertRaises(frappe.PermissionError):
                doc.save()
            with self.assertRaises(frappe.PermissionError):
                accept_request(name)
        finally:
            frappe.set_user("Administrator")
