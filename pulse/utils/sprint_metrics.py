"""Pure event replay used by both sprint charts and regression tests."""
from datetime import date, timedelta


def replay(events, start, end, measure="Tasks", today=None, baseline_scope=None, ideal_end=None):
    start, end = date.fromisoformat(str(start)[:10]), date.fromisoformat(str(end)[:10])
    today = today or date.today()
    ideal_end = date.fromisoformat(str(ideal_end)[:10]) if ideal_end else end
    events = sorted(events, key=lambda e: e['at'])
    states, index, rows = {}, 0, []
    day = start
    baseline_states = [e['state'] for e in events if e.get('kind') == 'Baseline']
    if baseline_scope is None and baseline_states:
        baseline_scope = sum(1 if measure == 'Tasks' else float(s.get(measure.lower(), 0) or 0)
                             for s in baseline_states if s['present'])
    while day <= end:
        while index < len(events) and events[index]['at'][:10] <= day.isoformat():
            state = events[index]['state']
            states[state['task']] = state
            index += 1
        active = [s for s in states.values() if s['present']]
        weight = lambda s: 1 if measure == 'Tasks' else float(s.get(measure.lower(), 0) or 0)
        scope = sum(weight(s) for s in active)
        completed = sum(weight(s) for s in active if s['completed'])
        if baseline_scope is None:
            baseline_scope = scope
        duration = (ideal_end - start).days
        ideal = baseline_scope * (1 - (day - start).days / duration) if duration > 0 else 0
        rows.append({'date': day.isoformat(), 'scope': scope if day <= today else None,
                     'completed': completed if day <= today else None,
                     'actual_remaining': scope - completed if day <= today else None,
                     'ideal_remaining': round(ideal, 2)})
        day += timedelta(days=1)
    return rows
