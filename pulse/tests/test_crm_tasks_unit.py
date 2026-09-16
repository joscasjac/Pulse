"""Adapter contract tests; no claim that the optional CRM app is installed."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import frappe
from pulse.api import crm_tasks


class CrmTaskTests(unittest.TestCase):
    def test_absent_app_is_explicit_and_never_queries_tasks(self):
        with patch.object(crm_tasks, "available", return_value=False), patch.object(frappe, "get_list") as listing:
            self.assertEqual(crm_tasks.mine(), {"available": False, "tasks": []})
            listing.assert_not_called()

    def test_parent_permission_and_unknown_reference_are_denied(self):
        with patch.object(frappe, "has_permission", return_value=False):
            self.assertFalse(crm_tasks._reference_allowed({"reference_doctype": "CRM Deal", "reference_docname": "1"}))
            self.assertFalse(crm_tasks._reference_allowed({"reference_doctype": "Customer", "reference_docname": "1"}))
            self.assertTrue(crm_tasks._reference_allowed({}))

    def test_identity_is_provider_qualified_and_reference_link_encoded(self):
        row = frappe._dict(name="12", reference_doctype="CRM Deal", reference_docname="a/b")
        with patch.object(frappe, "has_permission", return_value=True):
            result = crm_tasks._row(row)
        self.assertEqual(result["identity"], "frappe_crm:CRM Task:12")
        self.assertEqual(result["reference_url"], "/crm/deals/a%2Fb")

    def test_save_updates_source_document_without_task_copy(self):
        doc = MagicMock()
        doc.modified = "2026-09-16 12:00:00"
        doc.start_date = doc.due_date = None
        doc.meta.get_field.return_value.options = "Backlog\nTodo\nIn Progress\nDone\nCanceled"
        with patch.object(crm_tasks, "available", return_value=True), patch.object(frappe, "get_doc", return_value=doc) as lookup, patch.object(crm_tasks, "_reference_allowed", return_value=True), patch.object(crm_tasks, "_row", return_value={"status": "Done"}):
            result = crm_tasks.update("12", {"status": "Done"}, doc.modified)
        lookup.assert_called_once_with("CRM Task", "12")
        doc.check_permission.assert_any_call("read")
        doc.check_permission.assert_any_call("write")
        doc.update.assert_called_once_with({"status": "Done"})
        doc.save.assert_called_once()
        self.assertEqual(result["status"], "Done")

    def test_stale_save_does_not_write(self):
        doc = MagicMock(modified="new")
        def fail(*args, **kwargs):
            raise ValueError(args[0])
        with patch.object(crm_tasks, "available", return_value=True), patch.object(frappe, "get_doc", return_value=doc), patch.object(crm_tasks, "_reference_allowed", return_value=True), patch.object(frappe, "throw", side_effect=fail):
            with self.assertRaisesRegex(ValueError, "changed"):
                crm_tasks.update("12", {"status": "Done"}, "old")
        doc.save.assert_not_called()

    def test_restricted_parent_cannot_be_edited_even_if_task_writable(self):
        doc = MagicMock(modified="now")
        def fail(*args, **kwargs):
            raise PermissionError(args[0])
        with patch.object(crm_tasks, "available", return_value=True), patch.object(frappe, "get_doc", return_value=doc), patch.object(crm_tasks, "_reference_allowed", return_value=False), patch.object(frappe, "throw", side_effect=fail):
            with self.assertRaises(PermissionError):
                crm_tasks.update("12", {"status": "Done"}, "now")
        doc.save.assert_not_called()
