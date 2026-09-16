import unittest
from pulse.services.view_filters import validate_filter, matches


class ViewFiltersTest(unittest.TestCase):
    def test_nested_filters(self):
        tree = {'op': 'and', 'rules': [{'field': 'project', 'op': 'eq', 'value': 'Client'}, {'op': 'or', 'rules': [{'field': 'priority', 'op': 'eq', 'value': 'High'}, {'field': 'assignees', 'op': 'eq', 'value': 'me@example.com'}]}]}
        validate_filter(tree)
        self.assertTrue(matches({'project': 'Client', 'priority': 'Low', 'assignees': ['me@example.com']}, tree))
        self.assertFalse(matches({'project': 'Other', 'priority': 'High'}, tree))

    def test_overdue_excludes_completed(self):
        tree = {'field': 'exp_end_date', 'op': 'overdue'}
        self.assertTrue(matches({'exp_end_date': '2026-01-01', 'status': 'Open'}, tree, '2026-02-01'))
        self.assertFalse(matches({'exp_end_date': '2026-01-01', 'status': 'Completed'}, tree, '2026-02-01'))
        self.assertFalse(matches({}, tree, '2026-02-01'))

    def test_invalid_and_bounded_tree(self):
        for tree in [{'field': 'password', 'op': 'eq'}, {'op': 'xor', 'rules': []}, {'field': 'project', 'op': 'in', 'value': 'x'}]:
            with self.assertRaises(ValueError):
                validate_filter(tree)
        tree = {'op': 'and', 'rules': []}
        for _ in range(8):
            tree = {'op': 'and', 'rules': [tree]}
        with self.assertRaises(ValueError):
            validate_filter(tree)

    def test_labels_membership(self):
        self.assertTrue(matches({'labels': ['urgent', 'client']}, {'field': 'labels', 'op': 'in', 'value': ['client']}))
        self.assertFalse(matches({'labels': ['urgent']}, {'field': 'labels', 'op': 'eq', 'value': 'client'}))

    def test_typed_values_and_dates_from_database(self):
        from datetime import date
        self.assertTrue(matches({'exp_end_date': date(2026, 2, 1)},
                                {'field': 'exp_end_date', 'op': 'eq', 'value': '2026-02-01'}))
        self.assertTrue(matches({'expected_time': 3.0},
                                {'field': 'expected_time', 'op': 'in', 'value': ['3']}))
        self.assertFalse(matches({'expected_time': None},
                                 {'field': 'expected_time', 'op': 'eq', 'value': '0'}))
        for rule in [{'field': 'subject', 'op': 'overdue'},
                     {'field': 'exp_end_date', 'op': 'eq', 'value': '2026-02-30'},
                     {'field': 'expected_time', 'op': 'eq', 'value': 'NaN'},
                     {'field': 'priority', 'op': 'before', 'value': 'High'}]:
            with self.assertRaises(ValueError):
                validate_filter(rule)


if __name__ == '__main__':
    unittest.main()
