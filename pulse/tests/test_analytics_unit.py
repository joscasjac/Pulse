import unittest
from pulse.services.analytics import summarize


class AnalyticsTests(unittest.TestCase):
    def test_review_is_not_blocked_and_dependencies_are_deduplicated(self):
        tasks = [
            {"name": "review", "status": "Pending Review", "workflow_state": "In Review"},
            {"name": "waiting", "status": "Open"},
            {"name": "blocker", "status": "Working"},
            {"name": "done", "status": "Completed"},
        ]
        deps = [{"source_task": "waiting", "target_task": "blocker", "status": "Active"}] * 2
        result = summarize(tasks, deps, [], "2026-09-16")
        self.assertEqual(result["kpis"]["blocked"], 1)
        self.assertEqual(result["completion"]["pct"], 25)

    def test_resolved_or_invisible_dependency_does_not_leak(self):
        tasks = [{"name": "a", "status": "Open"}, {"name": "b", "status": "Completed"}]
        deps = [{"source_task": "a", "target_task": target, "status": "Active"} for target in ["b", "hidden"]]
        self.assertEqual(summarize(tasks, deps, [], "2026-09-16")["kpis"]["blocked"], 0)

    def test_custom_status_category_controls_blocking(self):
        tasks = [{"name": "waiting", "status": "Open", "workflow_state": "Waiting on client", "is_blocked": True},
                 {"name": "review", "status": "Pending Review", "workflow_state": "Blocked", "is_blocked": False}]
        self.assertEqual(summarize(tasks, [], [], "2026-09-16")["kpis"]["blocked"], 1)

    def test_cancelled_work_is_not_overdue_or_in_workload(self):
        tasks = [{"name": "a", "status": "Cancelled", "priority": "High", "exp_end_date": "2020-01-01", "_assign": '["person"]'}]
        result = summarize(tasks, [], [], "2026-09-16")
        self.assertEqual(result["kpis"]["delayed"], 0)
        self.assertEqual(result["kpis"]["flagged"], 0)
        self.assertEqual(result["workload"], [])
