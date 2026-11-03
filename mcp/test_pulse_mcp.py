"""Invoke registered tools through the real FastMCP SDK, without HTTP or credentials.

Run with the environment that installed mcp/requirements.txt:
    python -m unittest discover -s mcp -p 'test_pulse_mcp.py'
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from mcp.server.fastmcp.exceptions import ToolError


SERVER_PATH = Path(__file__).with_name('pulse_mcp_server.py')
exists = os.path.exists


def _test_path_exists(path):
    # Loading the test server must never read the developer's credential file.
    if isinstance(path, (str, os.PathLike)) and Path(path).name == '.pulse.env':
        return False
    return exists(path)


with patch('os.path.exists', side_effect=_test_path_exists), patch.dict(os.environ, {
        'PULSE_SITE_URL': 'https://qa.invalid', 'PULSE_API_KEY': '', 'PULSE_API_SECRET': ''}):
    spec = importlib.util.spec_from_file_location('pulse_mcp_under_test', SERVER_PATH)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)


class TestPulseWorkSDK(unittest.IsolatedAsyncioTestCase):
    async def test_list_result_passes_sdk_output_conversion(self):
        expected = [{'name': 'PAGE-QA-1'}, {'name': 'PAGE-QA-2'}]
        with patch.object(server, 'call', return_value=expected) as call:
            content = await server.mcp.call_tool('pulse_work', {'operation': 'list_pages', 'values': {'project': 'PROJ-QA'}})
        self.assertEqual([json.loads(item.text) for item in content], expected)
        call.assert_called_once_with('pulse.api.automation.execute', operation='list_pages', values={'project': 'PROJ-QA'})

    async def test_object_result_passes_sdk_output_conversion(self):
        expected = {'name': 'TASK-QA', 'subject': 'SDK acceptance'}
        with patch.object(server, 'call', return_value=expected) as call:
            content = await server.mcp.call_tool('pulse_work', {'operation': 'get_task', 'values': {'task': 'TASK-QA'}})
        self.assertEqual(json.loads(content[0].text), expected)
        call.assert_called_once_with('pulse.api.automation.execute', operation='get_task', values={'task': 'TASK-QA'})

    async def test_registration_accepts_any_json_shape_and_sdk_validates_inputs(self):
        tool = next(item for item in await server.mcp.list_tools() if item.name == 'pulse_work')
        self.assertIsNone(tool.outputSchema)
        with patch.object(server, 'call') as call:
            with self.assertRaises(ToolError):
                await server.mcp.call_tool('pulse_work', {'operation': 'list_pages', 'values': []})
        call.assert_not_called()
