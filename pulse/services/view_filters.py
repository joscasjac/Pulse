"""Bounded, typed filter trees shared by all task presentations."""
from datetime import date
import math

FIELDS = {'name', 'creation', 'modified', 'owner', 'subject', 'project', 'workflow_state', 'priority', 'type', 'assignees', 'labels', 'exp_start_date', 'exp_end_date', 'expected_time', 'pulse_story_points'}
DATE_FIELDS = {'exp_start_date', 'exp_end_date'}
NUMBER_FIELDS = {'expected_time', 'pulse_story_points'}
OPS = {'eq', 'ne', 'contains', 'in', 'before', 'after', 'empty', 'overdue'}


def validate_filter(node, depth=0, budget=None):
    budget = [200] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError("A view supports at most 200 filter rules and groups.")
    if not isinstance(node, dict) or depth > 6:
        raise ValueError('Filters must be objects nested at most six levels.')
    if 'rules' in node:
        if node.get('op') not in ('and', 'or') or not isinstance(node['rules'], list) or len(node['rules']) > 30:
            raise ValueError('Choose AND or OR with at most 30 rules per group.')
        for child in node['rules']:
            validate_filter(child, depth + 1, budget)
    elif node.get('field') not in FIELDS or node.get('op') not in OPS:
        raise ValueError('Unknown filter field or operator.')
    elif node['op'] == 'in' and not isinstance(node.get('value'), list):
        raise ValueError('The in operator requires a list.')
    if 'rules' not in node:
        field, op, value = node['field'], node['op'], node.get('value')
        if op == 'overdue' and field not in DATE_FIELDS:
            raise ValueError('Overdue requires a date field.')
        if op in ('before', 'after') and field not in DATE_FIELDS | NUMBER_FIELDS:
            raise ValueError('Before and after require a date or number field.')
        if op not in ('empty', 'overdue'):
            values = value if op == 'in' else [value]
            for item in values:
                if not isinstance(item, (str, int, float)) or isinstance(item, bool):
                    raise ValueError('Filter values must be text, dates or numbers.')
                if field in DATE_FIELDS:
                    try:
                        date.fromisoformat(str(item))
                    except ValueError:
                        raise ValueError('Use a valid ISO date in date filters.')
                if field in NUMBER_FIELDS:
                    try:
                        if not math.isfinite(float(item)):
                            raise ValueError()
                    except (ValueError, TypeError):
                        raise ValueError('Use a finite number in numeric filters.')
    return node


def matches(row, node, today=None):
    if 'rules' in node:
        checks = [matches(row, c, today) for c in node['rules']]
        return (all(checks) if node['op'] == 'and' else any(checks)) if checks else True
    value, expected, op = row.get(node['field']), node.get('value'), node['op']
    if op == 'empty':
        return value in (None, '', [])
    if op == 'overdue':
        return bool(value and str(value)[:10] < (today or date.today().isoformat()) and row.get('status') not in ('Completed', 'Cancelled'))
    if node['field'] in NUMBER_FIELDS and op == 'in':
        try:
            return value is not None and float(value) in [float(v) for v in expected]
        except (TypeError, ValueError):
            return False
    if node['field'] in NUMBER_FIELDS and op != 'empty':
        try:
            if value is None:
                return op == 'ne'
            value, expected = float(value), float(expected)
        except (TypeError, ValueError):
            return False
    if node['field'] in DATE_FIELDS and value is not None:
        value = str(value)[:10]
    if op in ('before', 'after'):
        if value is None or expected is None:
            return False
        if node['field'] not in ('expected_time', 'pulse_story_points'):
            value, expected = str(value), str(expected)
        return value < expected if op == 'before' else value > expected
    if op == 'contains':
        return str(expected or '').casefold() in str(value or '').casefold()
    values = value if isinstance(value, list) else [value]
    if op == 'in':
        return any(v in expected for v in values)
    equal = expected in values
    return not equal if op == 'ne' else equal
