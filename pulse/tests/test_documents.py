"""Exercise document isolation, backlinks, sanitization and edit conflicts on Frappe."""
import frappe
from frappe.tests import IntegrationTestCase

class TestDocuments(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        from pulse.erpnext_bridge import ensure_default_company
        self.project = frappe.get_doc({"doctype":"Project", "project_name":"Docs "+frappe.generate_hash(length=8), "company":ensure_default_company()}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_template_search_revision_and_conflict(self):
        from pulse.api.documents import save_page, list_pages, revisions
        page=save_page(self.project.name, "Brief", template="brief")
        self.assertIn("Outcome",page["content"])
        saved=save_page(self.project.name,"Decision", "<p>Searchable evidence</p>", name=page["name"],modified=page["modified"])
        self.assertTrue(list_pages(self.project.name,"evidence"))
        self.assertTrue(revisions(page["name"]))
        with self.assertRaises(frappe.TimestampMismatchError):
            save_page(self.project.name,"Stale",name=page["name"],modified=page["modified"])
        self.assertEqual(frappe.db.get_value("Pulse Document",page["name"],"title"),"Decision")
        with self.assertRaises(frappe.TimestampMismatchError):
            save_page(self.project.name, "Overwritten details", name=page["name"], modified=saved["modified"], base_details={"title": "Brief", "tasks": []})

    def test_task_link_backlink_and_cross_project_rejection(self):
        from pulse.api.documents import save_page, task_pages
        task=frappe.get_doc({"doctype":"Task","subject":"Linked","project":self.project.name}).insert()
        page=save_page(self.project.name,"Linked page",tasks=[task.name])
        self.assertEqual(task_pages(task.name)[0]["name"],page["name"])
        other=frappe.get_doc({"doctype":"Task","subject":"Unscoped"}).insert()
        with self.assertRaises(frappe.ValidationError):
            save_page(self.project.name,"Bad link",tasks=[other.name])

    def test_html_sanitization_and_guest_isolation(self):
        from pulse.api.documents import save_page,get_page,add_comment
        page=save_page(self.project.name,"Safe",'<script>alert(1)</script><p onclick="alert(2)">Hello</p>')
        self.assertNotIn('<script',page['content'])
        self.assertNotIn('onclick',page['content'])
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_page(page["name"])
        with self.assertRaises(frappe.PermissionError):
            add_comment(page["name"],"Unauthorized")

    def test_collaboration_concurrent_states_are_persisted_and_compacted(self):
        from pulse.api.documents import save_page, sync_page, get_page
        import json
        from pathlib import Path
        page = save_page(self.project.name, 'Together', '<p>Original</p>')
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'document_crdt.json').read_text())
        first, second, merged = fixture['alice'], fixture['bob'], fixture['merged']
        a = sync_page(page['name'], sequence=0, state=first, initialize=1)
        b = sync_page(page['name'], sequence=a['sequence'], state=second, content='<p>Second</p>')
        concurrent = sync_page(page['name'], sequence=a['sequence'], state=first, content='<p>Stale projection</p>')
        self.assertEqual(concurrent['states'], [second, first])
        self.assertEqual(get_page(page['name'])['content'], '<p>Second</p>')
        reconnected = sync_page(page['name'])
        self.assertEqual(reconnected['states'], concurrent['states'])
        compact = sync_page(page['name'], sequence=concurrent['sequence'], state=merged, content='<p>Merged</p>')
        self.assertEqual(compact['states'], [merged])
        self.assertEqual(get_page(page['name'])['content'], '<p>Merged</p>')
        race = sync_page(page['name'], sequence=0, state=first, initialize=1)
        self.assertEqual(race['states'], [merged])
        with self.assertRaises(frappe.ValidationError):
            sync_page(page['name'], state='invalid base64!')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            sync_page(page['name'])
        with self.assertRaises(frappe.PermissionError):
            sync_page(page['name'], state=first)

    def test_collaboration_viewer_and_outsider_boundaries(self):
        from pulse.api.documents import save_page, sync_page
        import json
        from pathlib import Path
        state = json.loads((Path(__file__).parent / 'fixtures' / 'document_crdt.json').read_text())['baseline']
        suffix = frappe.generate_hash(length=8)
        viewer = f'doc-viewer-{suffix}@example.com'
        outsider = f'doc-outsider-{suffix}@example.com'
        for email in (viewer, outsider):
            frappe.get_doc({'doctype': 'User', 'email': email, 'first_name': 'Doc Reader',
                'send_welcome_email': 0, 'roles': [{'role': 'Pulse Viewer'}]}).insert()
        self.project.append('users', {'user': viewer, 'welcome_email_sent': 1})
        self.project.save()
        page = save_page(self.project.name, 'Private shared page')
        sync_page(page['name'], state=state, initialize=1)
        frappe.set_user(viewer)
        self.assertEqual(sync_page(page['name'])['states'], [state])
        from unittest.mock import patch
        from pulse.pulse.doctype.pulse_document.pulse_document import publish_page_update
        with patch("frappe.publish_realtime") as publish:
            publish_page_update(page['name'])
        reader_events = [call for call in publish.call_args_list if call.kwargs.get("user") == viewer]
        self.assertEqual({call.args[0] for call in reader_events}, {"pulse_page_updated", "doc_update", "list_update"})
        self.assertTrue(all("docname" not in call.kwargs and "doctype" not in call.kwargs for call in publish.call_args_list))
        with self.assertRaises(frappe.PermissionError):
            sync_page(page['name'], state=state)
        frappe.set_user(outsider)
        with self.assertRaises(frappe.PermissionError):
            sync_page(page['name'])

        frappe.set_user('Administrator')
        self.project.set('users', [])
        self.project.save()
        with patch("frappe.publish_realtime") as publish:
            publish_page_update(page['name'])
        self.assertFalse(any(call.kwargs.get('user') in {viewer, outsider} for call in publish.call_args_list))

    def test_collaboration_retries_only_its_own_transaction(self):
        from unittest.mock import patch
        from pulse.api.documents import sync_page
        with patch.object(frappe.db, 'transaction_writes', 0), patch.object(frappe.db, 'rollback') as rollback:
            with patch('pulse.api.documents._sync_page', side_effect=[frappe.QueryDeadlockError(), {'sequence': 2}]) as exchange:
                self.assertEqual(sync_page('test-page'), {'sequence': 2})
                self.assertEqual(exchange.call_count, 2)
                rollback.assert_called_once()
        with patch.object(frappe.db, 'transaction_writes', 1), patch.object(frappe.db, 'rollback') as rollback:
            with patch('pulse.api.documents._sync_page', side_effect=frappe.QueryDeadlockError()):
                with self.assertRaises(frappe.QueryDeadlockError):
                    sync_page('test-page')
                rollback.assert_not_called()
