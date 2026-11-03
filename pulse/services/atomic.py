"""Savepoint scope that also stages Frappe transaction callbacks.

Use only around handlers that do not commit internally. A successful scope merges
callbacks into the outer transaction; a failed scope cannot send stale notifications
when its caller catches the error and later commits unrelated work.
"""
from contextlib import contextmanager
import frappe
from frappe.utils import CallbackManager


@contextmanager
def atomic_scope(label='pulse'):
    name = label + '_' + frappe.generate_hash(length=10)
    frappe.db.savepoint(name)
    events = ('before_commit', 'after_commit', 'before_rollback', 'after_rollback')
    previous = {event: getattr(frappe.db, event) for event in events}
    staged = {event: CallbackManager() for event in events}
    for event in events:
        setattr(frappe.db, event, staged[event])
    try:
        yield
    except BaseException:
        try:
            staged['before_rollback'].run()
        except Exception:
            frappe.log_error(title='Pulse atomic rollback cleanup failed', message=frappe.get_traceback())
        try:
            frappe.db.rollback(save_point=name)
        finally:
            try:
                staged['after_rollback'].run()
            except Exception:
                frappe.log_error(title='Pulse atomic rollback cleanup failed', message=frappe.get_traceback())
        raise
    else:
        for event in events:
            previous[event].add(staged[event].run)
    finally:
        for event in events:
            setattr(frappe.db, event, previous[event])
