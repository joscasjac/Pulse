"""Pulse analytics (canonical namespace: pulse.api.analytics.*).

Aggregates for the MindPro-style analytics dashboard. All standalone Pulse data.
"""

import frappe
from frappe.utils import today


def _group(field):
    rows = frappe.db.sql(
        f"""SELECT `{field}` AS k, COUNT(name) AS c FROM `tabPulse Task`
            WHERE `{field}` IS NOT NULL AND `{field}` != ''
            GROUP BY `{field}` ORDER BY c DESC""",
        as_dict=True,
    )
    return [{"label": r.k, "value": r.c} for r in rows]


@frappe.whitelist()
def get_analytics(project=None):
    cond = ""
    args = {}
    if project:
        cond = " AND project = %(project)s"
        args["project"] = project

    def count(where):
        return frappe.db.sql(
            f"SELECT COUNT(name) FROM `tabPulse Task` WHERE {where}{cond}", args
        )[0][0]

    completed = count("status = 'Completed'")
    delayed = count(
        f"exp_end_date < '{today()}' AND status NOT IN ('Completed','Cancelled')"
    )
    blocked = count("workflow_state = 'In Review'")
    flagged = count("priority IN ('High','Critical','Urgent') AND status NOT IN ('Completed','Cancelled')")

    # story point completion
    est = frappe.db.sql(
        f"SELECT COALESCE(SUM(pulse_story_points),0) FROM `tabPulse Task` WHERE 1=1{cond}", args
    )[0][0] or 0
    done_pts = frappe.db.sql(
        f"SELECT COALESCE(SUM(pulse_story_points),0) FROM `tabPulse Task` WHERE status='Completed'{cond}", args
    )[0][0] or 0

    # workload per assignee
    workload = {}
    for a in frappe.db.get_all("Pulse Task",
                               filters={"status": ["not in", ["Completed", "Cancelled"]]},
                               fields=["_assign"]):
        for u in (frappe.parse_json(a._assign or "[]") or []):
            workload[u] = workload.get(u, 0) + 1
    workload_series = [
        {"label": k.split("@")[0], "value": v}
        for k, v in sorted(workload.items(), key=lambda x: -x[1])[:8]
    ]

    # sprint progress
    sprints = []
    for s in frappe.db.get_all("Pulse Sprint",
                               fields=["name", "sprint_name", "status"],
                               order_by="start_date desc", limit=6):
        total = frappe.db.count("Pulse Task", {"pulse_sprint": s.name})
        done = frappe.db.count("Pulse Task", {"pulse_sprint": s.name, "status": "Completed"})
        sprints.append({
            "name": s.sprint_name or s.name, "status": s.status,
            "total": total, "done": done,
            "pct": round((done / total) * 100) if total else 0,
        })

    return {
        "kpis": {"completed": completed, "blocked": blocked, "flagged": flagged, "delayed": delayed},
        "status_distribution": _group("status"),
        "type_distribution": _group("task_type"),
        "workload": workload_series,
        "storypoints": {"estimated": float(est), "completed": float(done_pts),
                        "pct": round((done_pts / est) * 100) if est else 0},
        "sprint_progress": sprints,
    }
