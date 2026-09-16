import uuid
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api.modules import save_module, set_tasks, get_module, task_modules

class TestModules(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.project=frappe.get_doc(dict(doctype='Project',project_name='Modules '+uuid.uuid4().hex[:8])).insert()
        self.module=save_module(self.project.name,'Feature')
        self.tasks=[]

    def tearDown(self):
        frappe.set_user('Administrator')
        for n in frappe.get_all('Pulse Module Task',filters={'project':self.project.name},pluck='name'):
            frappe.delete_doc('Pulse Module Task',n,force=True)
        for n in frappe.get_all('Pulse Module',filters={'project':self.project.name},pluck='name'):
            frappe.delete_doc('Pulse Module',n,force=True)
        for t in self.tasks:
            frappe.delete_doc('Task',t.name,force=True)
        frappe.delete_doc('Project',self.project.name,force=True)

    def task(self,subject):
        t=frappe.get_doc(dict(doctype='Task',project=self.project.name,subject=subject)).insert()
        self.tasks.append(t)
        return t

    def test_progress_many_to_many_and_exclusions(self):
        a=self.task('A'); b=self.task('B'); c=self.task('C')
        a.db_set('status','Completed'); c.db_set('pulse_archived',1)
        result=set_tasks(self.module['name'],[a.name,b.name,c.name])
        self.assertEqual((result['percentage'],result['total']),(50,2))
        second=save_module(self.project.name,'Other')
        set_tasks(second['name'],[a.name])
        self.assertEqual(len(task_modules(a.name)['modules']),2)
        set_tasks(self.module['name'],[a.name])
        self.assertEqual(get_module(self.module['name'])['total'],2)
        b.db_set('status','Cancelled')
        self.assertEqual(get_module(self.module['name'])['percentage'],100)
        set_tasks(self.module['name'],[a.name],remove=1)
        self.assertEqual(get_module(self.module['name'])['percentage'],0)

    def test_scope_and_invalid_dates(self):
        with self.assertRaises(frappe.ValidationError):
            save_module(self.project.name,'Bad',start_date='2026-09-20',due_date='2026-09-10')
        t=self.task('Scope')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            get_module(self.module['name'])
        with self.assertRaises(frappe.PermissionError):
            set_tasks(self.module['name'],[t.name])

    def test_hidden_tasks_do_not_affect_progress_or_membership_lists(self):
        a=self.task('Visible'); b=self.task('Hidden completed')
        b.db_set('status','Completed')
        set_tasks(self.module['name'],[a.name,b.name])
        email='module-junior-'+uuid.uuid4().hex[:8]+'@example.com'
        user=frappe.get_doc(dict(doctype='User',email=email,first_name='Module tester',send_welcome_email=0,roles=[{'role':'Pulse Junior Developer'}])).insert()
        self.project.reload()
        self.project.append('users',{'user':email,'welcome_email_sent':1}); self.project.save()
        a.db_set('owner',email)
        try:
            frappe.set_user(email)
            result=get_module(self.module['name'])
            self.assertEqual((result['total'],result['percentage']),(1,0))
            rows=frappe.get_list('Pulse Module Task',filters={'module':self.module['name']},fields=['task'],limit_page_length=0)
            self.assertEqual([r.task for r in rows],[a.name])
            hidden=frappe.db.get_value('Pulse Module Task',{'task':b.name},'name')
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc('Pulse Module Task',hidden).check_permission('read')
        finally:
            frappe.set_user('Administrator')
            self.project.set('users',[]);self.project.save()
            a.db_set('owner','Administrator')
            frappe.delete_doc('User',user.name,force=True)

    def test_project_move_clears_membership(self):
        task=self.task('Move project')
        set_tasks(self.module['name'],[task.name])
        destination=frappe.get_doc(dict(doctype='Project',project_name='Module destination '+uuid.uuid4().hex[:8])).insert()
        try:
            task.project=destination.name
            task.save()
            self.assertEqual(get_module(self.module['name'])['total'],0)
            self.assertEqual(task_modules(task.name)['modules'],[])
            self.assertFalse(frappe.db.exists('Pulse Module Task',{'task':task.name}))
        finally:
            task.project=self.project.name;task.save()
            frappe.delete_doc('Project',destination.name,force=True)
