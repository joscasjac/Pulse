import frappe

frappe.set_user("Administrator")
ok, fail = [], []

def t(label, fn):
    try:
        fn()
        ok.append(label)
    except Exception as e:
        fail.append(f"{label}: {type(e).__name__} {str(e)[:90]}")

# module list endpoints (retained doctypes)
for dt in ["Pulse Objective", "Pulse Risk", "Pulse Meeting", "Pulse Portfolio",
           "Pulse Retrospective", "Pulse Document", "Pulse Timesheet", "Pulse Sprint"]:
    t(f"list {dt}", lambda dt=dt: frappe.get_all(dt, limit=1))

from pulse.api.spa import get_board, get_task
from pulse.api.analytics import get_analytics
from pulse.api.audit import get_audit_log
from pulse.api.dashboards import get_my_dashboard, get_dashboard_stats

t("get_board", lambda: get_board())
t("get_analytics", lambda: get_analytics())
t("get_audit_log", lambda: get_audit_log(limit=5))
t("get_dashboard_stats", lambda: get_dashboard_stats())
t("get_my_dashboard", lambda: get_my_dashboard())
_task = frappe.get_all("Task", filters={"issue_key": ["is", "set"]}, pluck="name")
if _task:
    t("get_task(drawer)", lambda: get_task(_task[0]))

# permission path as a non-admin (junior dev)
def as_junior():
    frappe.set_user("erin@pulse.demo")
    b = get_board()
    frappe.set_user("Administrator")
    return b
t("get_board as junior (perm path)", as_junior)

print("SMOKE_OK", len(ok))
print("SMOKE_FAIL", len(fail))
for f in fail:
    print("  FAIL", f)
