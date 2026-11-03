import csv
import io
import frappe
from frappe.tests import IntegrationTestCase
from pulse.api import transfer


class TestCsvTransfer(IntegrationTestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.project = frappe.get_doc({'doctype': 'Project', 'project_name': 'CSV acceptance ' + frappe.generate_hash(length=8)}).insert()

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_preview_import_replay_and_update(self):
        content = 'subject,priority,expected_time\n"First, task",High,2\nSecond,Low,1\n'
        preview = transfer.preview_import(self.project.name, content)
        self.assertEqual((preview['create'], preview['update']), (2, 0))
        result = transfer.import_tasks(self.project.name, content)
        self.assertEqual(len(result['created']), 2)
        self.assertTrue(transfer.import_tasks(self.project.name, content)['replayed'])
        self.assertEqual(frappe.db.count('Task', {'project': self.project.name}), 2)
        name = result['created'][0]
        changed = f'name,subject,priority\n{name},Updated,Urgent\n'
        self.assertEqual(transfer.import_tasks(self.project.name, changed)['updated'], [name])
        self.assertEqual(frappe.get_doc('Task', name).priority, 'Urgent')
        self.assertEqual(frappe.get_doc('Task', name).expected_time, 2)

    def test_bad_row_rolls_back_every_created_task_and_batch(self):
        with self.assertRaises(frappe.ValidationError):
            transfer.import_tasks(self.project.name, 'subject,expected_time\nValid,1\nInvalid,-2\n')
        self.assertEqual(frappe.db.count('Task', {'project': self.project.name}), 0)
        self.assertEqual(frappe.db.count('Pulse Import Batch', {'project': self.project.name}), 0)

    def test_rejects_privileged_columns_duplicate_ids_and_cross_project_updates(self):
        for content in ('subject,expected_time\nBad,not-a-number\n', 'subject,expected_time\nBad,nan\n', 'subject,owner\nTest,Administrator\n', 'subject,subject\nA,B\n', 'subject,priority\nA\n'):
            with self.assertRaises(frappe.ValidationError):
                transfer.preview_import(self.project.name, content)
        other = frappe.get_doc({'doctype': 'Project', 'project_name': 'Other CSV project'}).insert()
        task = frappe.get_doc({'doctype': 'Task', 'subject': 'Other', 'project': other.name}).insert()
        with self.assertRaises(frappe.ValidationError):
            transfer.import_tasks(self.project.name, f'name,subject\n{task.name},Changed\n')
        with self.assertRaises(frappe.ValidationError):
            transfer.preview_import(other.name, f'name,subject\n{task.name},A\n{task.name},B\n')

    def test_export_quotes_formula_cells_and_keeps_csv_escaping(self):
        frappe.get_doc({'doctype': 'Task', 'project': self.project.name,
                        'subject': '=HYPERLINK("https://example.test")', 'description': 'Line one\nLine two'}).insert()
        exported = transfer.export_tasks(self.project.name)
        rows = list(csv.DictReader(io.StringIO(exported['content'])))
        self.assertEqual(exported['count'], 1)
        self.assertTrue(rows[0]['subject'].startswith("'="))
        self.assertIn('Line two', rows[0]['description'])
        transfer.import_tasks(self.project.name, exported['content'])
        self.assertEqual(frappe.get_doc('Task', rows[0]['name']).subject, '=HYPERLINK("https://example.test")')
        self.assertEqual(transfer._cell(-12.25), '-12.25')

    def test_configured_required_custom_field_round_trips_in_csv(self):
        fieldname = 'custom_csv_' + frappe.generate_hash(length=8)
        field = frappe.get_doc({'doctype': 'Custom Field', 'dt': 'Task', 'label': 'CSV acceptance field',
            'fieldname': fieldname, 'fieldtype': 'Float', 'insert_after': 'description'}).insert()
        try:
            self.project.reload()
            self.project.append('pulse_task_field_rules', {'fieldname': fieldname,
                'required_statuses': 'To Do', 'show_in_form': 1})
            self.project.save()
            content = f'subject,{fieldname}\nRequired field task,-12.25\n'
            result = transfer.import_tasks(self.project.name, content)
            self.assertEqual(frappe.get_doc('Task', result['created'][0]).get(fieldname), -12.25)
            self.assertIn(fieldname, transfer.csv_template(self.project.name)['content'])
            exported = list(csv.DictReader(io.StringIO(transfer.export_tasks(self.project.name)['content'])))
            self.assertEqual(exported[0][fieldname], '-12.25')
        finally:
            frappe.set_user('Administrator')
            for name in frappe.get_all('Task', filters={'project': self.project.name}, pluck='name'):
                frappe.delete_doc('Task', name, force=True)
            frappe.db.delete('Pulse Import Batch', {'project': self.project.name})
            frappe.delete_doc('Project', self.project.name, force=True)
            frappe.delete_doc('Custom Field', field.name)
            frappe.clear_cache(doctype='Task')
            # Custom Field insertion performs native DDL and commits this fixture.
            # Persist only its explicit cleanup; tearDown rollback would restore
            # the deleted Custom Field metadata and leave ghost CSV fields.
            frappe.db.commit()
