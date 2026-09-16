"""Hook registry must survive handler imports and Frappe cache refreshes."""
import subprocess
import sys
import unittest
from pathlib import Path


class HookRegistryTests(unittest.TestCase):
    def test_event_import_does_not_replace_doc_events_dictionary(self):
        # Isolate package imports from other tests' mocked Frappe modules.
        script = """
import importlib
import sys
import types
frappe = types.ModuleType('frappe')
utils = types.ModuleType('frappe.utils')
utils.now_datetime = lambda: None
sys.modules['frappe'] = frappe
sys.modules['frappe.utils'] = utils
hooks = importlib.import_module('pulse.hooks')
before = hooks.doc_events
importlib.import_module('pulse.hooks.events.task')
assert isinstance(hooks.doc_events, dict), 'Handler import replaced the hook registry'
assert hooks.doc_events is before
assert hooks.doc_events['Task']['before_validate'] == [
    'pulse.hooks.permissions.preserve_private_task_links',
    'pulse.api.task_config.validate_task',
]
# Frappe ignores module-valued attributes when rebuilding its hooks cache.
visible = {k: v for k, v in vars(hooks).items() if not isinstance(v, types.ModuleType)}
assert visible['doc_events']['Task'] == before['Task']
"""
        subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).parents[2], check=True)
