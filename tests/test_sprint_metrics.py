import unittest
from datetime import date
from pulse.utils.sprint_metrics import replay


def event(day, task, present=True, completed=False, hours=3, points=2):
    return {'at': f'2026-01-{day:02d} 12:00:00', 'state': {'task': task, 'present': present, 'completed': completed, 'hours': hours, 'points': points}}


class SprintHistoryTests(unittest.TestCase):
    def test_membership_completion_reopen_and_estimate_changes(self):
        events = [event(1, 'a'), event(2, 'a', completed=True), event(3, 'a'),
                  event(3, 'b', hours=5), event(4, 'a', present=False), event(5, 'b', hours=8)]
        rows = replay(events, '2026-01-01', '2026-01-05', 'Hours', today=date(2026, 1, 5))
        self.assertEqual([r['actual_remaining'] for r in rows], [3, 0, 8, 5, 8])
        self.assertEqual([r['scope'] for r in rows], [3, 3, 8, 5, 8])

    def test_future_is_unknown_not_flat_projection(self):
        rows = replay([event(1, 'a')], '2026-01-01', '2026-01-03', today=date(2026, 1, 1))
        self.assertIsNone(rows[1]['actual_remaining'])
        self.assertEqual(rows[2]['ideal_remaining'], 0)

    def test_ideal_preserves_baseline_after_same_day_scope_change(self):
        initial = event(1, 'a', hours=3)
        initial['kind'] = 'Baseline'
        initial['at'] = '2026-01-01 09:00:00'
        rows = replay([initial, event(1, 'b', hours=5)], '2026-01-01', '2026-01-03', 'Hours', today=date(2026, 1, 3))
        self.assertEqual(rows[0]['scope'], 8)
        self.assertEqual(rows[0]['ideal_remaining'], 3)
        self.assertEqual(rows[1]['ideal_remaining'], 1.5)

    def test_empty_commitment_stays_zero_after_scope_added(self):
        rows = replay([event(1, 'a')], '2026-01-01', '2026-01-03',
                      today=date(2026, 1, 3), baseline_scope=0)
        self.assertEqual(rows[0]['scope'], 1)
        self.assertEqual([r['ideal_remaining'] for r in rows], [0, 0, 0])

    def test_early_close_preserves_scheduled_ideal(self):
        rows = replay([event(1, 'a', hours=8)], '2026-01-01', '2026-01-02',
                      'Hours', today=date(2026, 1, 2), ideal_end='2026-01-05')
        self.assertEqual([r['ideal_remaining'] for r in rows], [8, 6])

    def test_points_and_same_day_order(self):
        rows = replay([event(1, 'a'), event(2, 'a', completed=True)], '2026-01-01', '2026-01-02', 'Points', today=date(2026, 1, 3))
        self.assertEqual([r['completed'] for r in rows], [0, 2])

if __name__ == '__main__':
    unittest.main()
