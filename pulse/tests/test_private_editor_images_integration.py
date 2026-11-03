"""Persist real private editor-image files and revoke access with the parent."""
import base64
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.file_manager import save_file
from pulse.api import documents, spa


class TestPrivateEditorImages(IntegrationTestCase):
    def test_native_image_html_parent_binding_and_uploader_revocation(self):
        frappe.set_user('Administrator')
        user = 'private-image-' + frappe.generate_hash(length=8) + '@example.test'
        with patch('frappe.sendmail'):
            frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Image tester',
                'send_welcome_email': 0, 'roles': [{'role': 'Projects User'}, {'role': 'Pulse Senior Developer'}]}).insert()
            project = frappe.get_doc({'doctype': 'Project', 'project_name': 'Private image acceptance ' + frappe.generate_hash(length=8),
                'users': [{'user': user, 'welcome_email_sent': 1}]}).insert()
            task = frappe.get_doc({'doctype': 'Task', 'subject': 'Private image task', 'project': project.name}).insert()
            page = frappe.get_doc({'doctype': 'Pulse Document', 'title': 'Private image page', 'project': project.name}).insert()
            frappe.set_user(user)
            png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
            attachments = []
            try:
                for doctype, parent, field in [('Task', task.name, 'description'), ('Pulse Document', page.name, 'content')]:
                    attachment = save_file('editor-private-' + frappe.generate_hash(length=10) + '.png', png,
                                           doctype, parent, is_private=1)
                    attachments.append(attachment)
                    path = Path(attachment.get_full_path())
                    self.addCleanup(lambda owned_path=path: owned_path.unlink(missing_ok=True))
                    self.assertTrue(path.is_file())
                    self.assertEqual(attachment.attached_to_doctype, doctype)
                    self.assertEqual(attachment.attached_to_name, parent)
                    self.assertTrue(attachment.is_private)
                    self.assertTrue(attachment.file_url.startswith('/private/files/'))
                    self.assertTrue(attachment.is_downloadable())
                    doc = frappe.get_doc(doctype, parent)
                    doc.set(field, '<p>Persisted editor image</p><img src="' + attachment.file_url + '" alt="Synthetic private QA image">')
                    doc.save()
                    data = spa.get_task(parent) if doctype == 'Task' else documents.get_page(parent)
                    self.assertIn(attachment.file_url, data[field])
                frappe.set_user('Administrator')
                project.reload(); project.set('users', []); project.save()
                frappe.set_user(user)
                for attachment in attachments:
                    attachment.reload()
                    self.assertEqual(attachment.owner, user)
                    self.assertFalse(attachment.is_downloadable())
                    self.assertFalse(frappe.has_permission('File', 'read', doc=attachment))
                for action in [lambda: spa.get_task(task.name), lambda: documents.get_page(page.name)]:
                    with self.assertRaises(frappe.PermissionError): action()
            finally:
                frappe.set_user('Administrator')
                frappe.db.rollback()
