"""Link searches must filter before pagination and retain only authorized selections."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class TestLinkOptions(unittest.TestCase):
    def setUp(self):
        source = ast.parse((Path(__file__).parents[1] / 'api' / 'spa.py').read_text())
        function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == 'link_options')
        function.decorator_list = []
        self.frappe = SimpleNamespace(get_meta=Mock(return_value=SimpleNamespace(title_field='project_name')),
            get_list=Mock(), has_permission=Mock(return_value=True))
        namespace = {'frappe': self.frappe}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'link_options', 'exec'), namespace)
        self.options = namespace['link_options']
        self.utils = patch.dict('sys.modules', {'frappe.utils': SimpleNamespace(cint=lambda value: int(value or 0))})
        self.utils.start()
        self.addCleanup(self.utils.stop)

    def test_search_applies_before_bounded_page(self):
        self.frappe.get_list.return_value = [{'name': 'OLD', 'project_name': 'Older project'}]
        result = self.options('Project', txt='Older', start=50)
        query = self.frappe.get_list.call_args.kwargs
        self.assertEqual(query['limit_start'], 50)
        self.assertEqual(query['limit_page_length'], 50)
        self.assertIn(['project_name', 'like', '%Older%'], query['or_filters'])
        self.assertEqual(result, [{'value': 'OLD', 'label': 'Older project'}])

    def test_selection_outside_page_retained_but_permission_denied_row_removed(self):
        self.frappe.get_list.side_effect = [[{'name': 'NEW', 'project_name': 'New'}], [{'name': 'OLD', 'project_name': 'Old'}]]
        self.assertEqual([r['value'] for r in self.options('Project', selected='OLD')], ['NEW', 'OLD'])
        self.assertEqual(self.frappe.get_list.call_args.kwargs['filters'], {'name': 'OLD'})
        self.frappe.get_list.side_effect = [[], [{'name': 'HIDDEN', 'project_name': 'Secret'}]]
        self.frappe.has_permission.return_value = False
        self.assertEqual(self.options('Project', selected='HIDDEN'), [])
