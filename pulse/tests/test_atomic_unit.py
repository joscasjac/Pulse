"""Savepoint notification callbacks must follow database success or rollback."""
from collections import deque
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch


class Callbacks:
    def __init__(self): self.functions = deque()
    def add(self, callback): self.functions.append(callback)
    def run(self):
        while self.functions: self.functions.popleft()()


class TestAtomicScope(TestCase):
    def setUp(self):
        self.db = SimpleNamespace(savepoint=Mock(), rollback=Mock(), **{
            name: Callbacks() for name in ('before_commit', 'after_commit', 'before_rollback', 'after_rollback')})
        self.frappe = SimpleNamespace(db=self.db, generate_hash=lambda **kw: 'scope', log_error=Mock(), get_traceback=lambda: 'cleanup error')
        spec = importlib.util.spec_from_file_location('atomic_under_test', Path(__file__).parents[1] / 'services' / 'atomic.py')
        self.atomic = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': SimpleNamespace(CallbackManager=Callbacks)}):
            spec.loader.exec_module(self.atomic)

    def test_success_merges_callbacks_in_order_and_keeps_existing_queue(self):
        events = []; original = self.db.after_commit
        original.add(lambda: events.append('existing'))
        with self.atomic.atomic_scope():
            self.db.after_commit.add(lambda: events.append('new'))
        self.assertIs(self.db.after_commit, original)
        self.assertEqual(events, [])
        original.run()
        self.assertEqual(events, ['existing', 'new'])
        self.db.rollback.assert_not_called()

    def test_failure_discards_commit_callbacks_runs_cleanup_and_preserves_prior_callbacks(self):
        events = []; original = self.db.after_commit
        original.add(lambda: events.append('existing'))
        with self.assertRaisesRegex(ValueError, 'failed'):
            with self.atomic.atomic_scope():
                self.db.after_commit.add(lambda: events.append('stale email'))
                self.db.before_commit.add(lambda: events.append('stale write'))
                self.db.before_rollback.add(lambda: events.append('before rollback'))
                self.db.after_rollback.add(lambda: events.append('after rollback'))
                raise ValueError('failed')
        self.assertEqual(events, ['before rollback', 'after rollback'])
        self.db.before_commit.run(); self.db.after_commit.run()
        self.assertEqual(events, ['before rollback', 'after rollback', 'existing'])
        self.db.rollback.assert_called_once_with(save_point='pulse_scope')

    def test_successful_inner_scope_is_discarded_when_outer_scope_fails(self):
        events = []
        with self.assertRaises(ValueError):
            with self.atomic.atomic_scope('outer'):
                with self.atomic.atomic_scope('inner'):
                    self.db.after_commit.add(lambda: events.append('inner email'))
                raise ValueError('outer failed')
        self.db.after_commit.run()
        self.assertEqual(events, [])

    def test_cleanup_failure_is_logged_and_database_is_still_rolled_back(self):
        with self.assertRaisesRegex(ValueError, 'original'):
            with self.atomic.atomic_scope():
                self.db.before_rollback.add(Mock(side_effect=RuntimeError('cleanup')))
                raise ValueError('original')
        self.db.rollback.assert_called_once()
        self.frappe.log_error.assert_called_once()
