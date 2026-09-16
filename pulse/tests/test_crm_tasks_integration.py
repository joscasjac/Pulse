"""Run on an isolated site with official Frappe CRM installed."""
import unittest
import frappe
from pulse.api import crm_tasks

class CRMIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not crm_tasks.available(): raise unittest.SkipTest('Optional Frappe CRM app is not installed')
        cls.user='crm-pulse-agent@example.test';cls.other='crm-pulse-other@example.test'
        for user in [cls.user,cls.other]:
            if not frappe.db.exists('User',user):
                frappe.get_doc(dict(doctype='User',email=user,first_name='CRM QA',send_welcome_email=0,roles=[dict(role='Sales User')])).insert()
        cls.lead=frappe.get_doc(dict(doctype='CRM Lead',first_name='Pulse visible lead',status='New',lead_owner=cls.user)).insert()
        cls.hidden=frappe.get_doc(dict(doctype='CRM Lead',first_name='Pulse hidden lead',status='New',lead_owner=cls.other)).insert()
        cls.task=frappe.get_doc(dict(doctype='CRM Task',title='Pulse source task',status='Todo',priority='Medium',assigned_to=cls.user,reference_doctype='CRM Lead',reference_docname=cls.lead.name)).insert()
        cls.secret=frappe.get_doc(dict(doctype='CRM Task',title='Restricted followup',status='Todo',priority='High',assigned_to=cls.user,reference_doctype='CRM Lead',reference_docname=cls.hidden.name)).insert()
    def setUp(self): frappe.set_user(self.user)
    def test_01_mine_checks_parent(self):
        result=crm_tasks.mine();self.assertTrue(result['available'])
        ids={str(t['name']) for t in result['tasks']}
        self.assertIn(str(self.task.name),ids);self.assertNotIn(str(self.secret.name),ids)
    def test_02_update_and_completion_share_same_record(self):
        native_count = frappe.db.count('Task') if frappe.db.exists('DocType', 'Task') else None
        before=frappe.get_doc('CRM Task',self.task.name)
        row=crm_tasks.update(self.task.name,{'title':'Edited in Pulse','status':'Done','start_date':'2026-09-16','due_date':'2026-09-17 15:30:00'},str(before.modified))
        self.assertEqual(row['status'],'Done')
        if native_count is not None:
            self.assertEqual(frappe.db.count('Task'), native_count)
        source=frappe.get_doc('CRM Task',self.task.name);self.assertEqual(source.title,'Edited in Pulse');self.assertEqual(source.status,'Done')
    def test_03_parent_denial(self):
        doc=frappe.get_doc('CRM Task',self.secret.name)
        with self.assertRaises(frappe.PermissionError): crm_tasks.update(doc.name,{'status':'Done'},str(doc.modified))
        self.assertEqual(frappe.db.get_value('CRM Task',doc.name,'status'),'Todo')
    def test_04_stale_edit_rejected(self):
        doc=frappe.get_doc('CRM Task',self.task.name);old=str(doc.modified)
        doc.title='Changed from CRM';doc.save()
        with self.assertRaises(frappe.TimestampMismatchError):crm_tasks.update(doc.name,{'title':'Stale change'},old)
        self.assertEqual(frappe.db.get_value('CRM Task',doc.name,'title'),'Changed from CRM')
    def test_05_native_role_denial(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):crm_tasks.update(self.task.name,{'status':'Todo'},str(self.task.modified))
    def test_06_invalid_dates_rejected(self):
        doc=frappe.get_doc('CRM Task',self.task.name)
        with self.assertRaises(frappe.ValidationError):crm_tasks.update(doc.name,{'start_date':'2026-09-20','due_date':'2026-09-10 12:00:00'},str(doc.modified))
    @classmethod
    def tearDownClass(cls):
        frappe.set_user('Administrator');frappe.db.rollback()

