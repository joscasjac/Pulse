import frappe
from frappe.utils import today, add_days
from datetime import timedelta
import random

DEMO_USERS = [
    "rajesh@demo.com",
    "priya@demo.com",
    "amit@demo.com",
    "deepa@demo.com",
    "vikram@demo.com",
    "neha@demo.com",
    "arjun@demo.com",
    "sara@demo.com",
]

def _get_project():
    return frappe.get_all("Pulse Project", pluck="name")[0]

def _get_sprints():
    return frappe.get_all("Pulse Sprint", pluck="name", order_by="creation asc")

def _get_tasks():
    return frappe.get_all("Pulse Task", pluck="name", order_by="creation asc")

def _get_task_subject(name):
    return frappe.db.get_value("Pulse Task", name, "subject")

def _make(dt, data):
    doc = frappe.get_doc({"doctype": dt, **data})
    doc.flags.ignore_permissions = True
    doc.flags.ignore_links = True
    doc.insert(ignore_if_duplicate=True, ignore_links=True, ignore_permissions=True)
    return doc.name

def _append(parent_doc, child_field, child_data):
    child = parent_doc.append(child_field, child_data)
    return child

def _make_child(parent, parenttype, parentfield, data):
    """Create a child table row directly (for simple cases where we don't need the parent)"""
    doc = frappe.get_doc({
        "doctype": frappe.get_meta(parenttype).get_field(parentfield).options,
        "parent": parent,
        "parenttype": parenttype,
        "parentfield": parentfield,
        **data
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_links = True
    doc.insert(ignore_links=True, ignore_permissions=True)
    return doc.name

def seed_okrs():
    project = _get_project()
    objectives = []

    obj_data = [
        {
            "objective_name": "Deliver a world-class Pulse v2.0 launch",
            "fiscal_year": "2026-2027",
            "quarter": "Q3",
            "category": "Company",
            "weight": 1.0,
        },
        {
            "objective_name": "Build a high-performing, sustainable engineering culture",
            "fiscal_year": "2026-2027",
            "quarter": "Q3",
            "category": "Team",
            "weight": 1.0,
        },
        {
            "objective_name": "Achieve 95% customer satisfaction on Pulse features",
            "fiscal_year": "2026-2027",
            "quarter": "Q3",
            "category": "Company",
            "weight": 1.0,
        },
    ]

    for od in obj_data:
        oid = _make("Pulse Objective", od)
        objectives.append(oid)
        print(f"  OKR: {od['objective_name']}")

    krs_data = [
        {
            "kr_name": "Ship all 10 planned Pulse features by Oct 1",
            "parent_objective": objectives[0],
            "kr_type": "Milestone",
            "weight": 1.0,
            "target_value": 10,
            "current_value": 4,
        },
        {
            "kr_name": "Achieve < 200ms p95 API response time",
            "parent_objective": objectives[0],
            "kr_type": "Metric",
            "unit": "ms",
            "weight": 0.8,
            "target_value": 200,
            "current_value": 350,
        },
        {
            "kr_name": "Reduce onboarding time for new team members to 1 week",
            "parent_objective": objectives[1],
            "kr_type": "Milestone",
            "weight": 1.0,
            "target_value": 1,
            "current_value": 0,
        },
        {
            "kr_name": "Conduct 4 team retrospectives this quarter",
            "parent_objective": objectives[1],
            "kr_type": "Metric",
            "unit": "retros",
            "weight": 0.5,
            "target_value": 4,
            "current_value": 2,
        },
        {
            "kr_name": "Resolve all P0/P1 bugs within 24 hours",
            "parent_objective": objectives[2],
            "kr_type": "Metric",
            "unit": "%",
            "weight": 1.0,
            "target_value": 100,
            "current_value": 75,
        },
        {
            "kr_name": "Zero critical security vulnerabilities in production",
            "parent_objective": objectives[2],
            "kr_type": "Metric",
            "unit": "vulns",
            "weight": 1.0,
            "target_value": 0,
            "current_value": 0,
        },
    ]

    for kr in krs_data:
        kid = _make("Pulse Key Result", kr)
        print(f"  KR: {kr['kr_name']} ({kr.get('unit', '')})")

    print("  OKR check-in...")
    for kr_data in krs_data:
        kid = frappe.get_all("Pulse Key Result", filters={"kr_name": kr_data["kr_name"]}, pluck="name")
        if kid:
            _make("Pulse OKR Check-in", {
                "key_result": kid[0],
                "check_in_date": add_days(today(), -random.randint(1, 14)),
                "new_value": kr_data["current_value"],
                "comment": "Initial seed check-in. Making steady progress.",
                "confidence_change": random.choice(["Up", "Same"]),
            })

def seed_risks():
    project = _get_project()
    tasks = _get_tasks()

    risks_data = [
        {
            "risk_title": "Key developer may leave mid-sprint",
            "project": project,
            "category": "Resource",
            "status": "Open",
            "probability": "3-Medium",
            "impact": "4-Major",
            "risk_score": 12,
            "risk_level": "High",
            "description": "One senior engineer has expressed burnout concerns.",
            "mitigation_plan": "Cross-train 2 junior devs on critical modules.",
            "contingency_plan": "Engage contract developer from shortlist.",
        },
        {
            "risk_title": "API integration with legacy system may fail",
            "project": project,
            "category": "Technical",
            "status": "Mitigated",
            "probability": "2-Low",
            "impact": "3-Moderate",
            "risk_score": 6,
            "risk_level": "Medium",
            "description": "Legacy integration uses outdated SOAP API.",
            "mitigation_plan": "Built adapter layer with timeout/retry.",
            "contingency_plan": "Fall back to CSV export/import.",
        },
        {
            "risk_title": "Budget overrun due to extended development",
            "project": project,
            "category": "Budget",
            "status": "Open",
            "probability": "3-Medium",
            "impact": "3-Moderate",
            "risk_score": 9,
            "risk_level": "High",
            "description": "Two features taking 30% longer than estimated.",
            "mitigation_plan": "Weekly budget review. Reprioritize backlog.",
            "contingency_plan": "Request extension. Reduce non-critical scope.",
        },
    ]

    for rd in risks_data:
        rid = _make("Pulse Risk", rd)
        print(f"  Risk: {rd['risk_title']} ({rd['status']})")

        if tasks and random.random() > 0.5:
            task = random.choice(tasks)
            _make_child(rid, "Pulse Risk", "linked_tasks", {"task": task})

def seed_retros():
    project = _get_project()
    sprints = _get_sprints()

    for i in range(2):
        sprint = sprints[-(i + 1)] if sprints else None
        retro_data = {
            "title": f"Sprint Retrospective — Week {i + 1}",
            "project": project,
            "sprint": sprint,
            "date_held": add_days(today(), -7 * (i + 1)),
            "template": "Start/Stop/Continue" if i == 0 else "Went Well/To Improve",
            "overall_sentiment": "😊",
            "facilitator": "rajesh@demo.com",
        }
        retro = frappe.get_doc({"doctype": "Pulse Retrospective", **retro_data})
        retro.flags.ignore_permissions = True
        retro.flags.ignore_links = True
        retro.append("participants", {"user": "rajesh@demo.com"})
        retro.append("participants", {"user": "priya@demo.com"})
        retro.append("participants", {"user": "amit@demo.com"})

        items = [
            ("Start", "Daily standup time-boxing"),
            ("Stop", "Multi-tasking across 3+ features"),
            ("Continue", "Thorough code reviews"),
        ] if i == 0 else [
            ("Went Well", "Sprint planning accuracy improved"),
            ("To Improve", "Better error handling in new code"),
        ]

        for cat, content in items:
            retro.append("items", {
                "category": cat,
                "content": content,
                "author": random.choice(DEMO_USERS),
                "votes": random.randint(1, 8),
                "discussion": "Team agreed to track this.",
            })

        retro.insert(ignore_if_duplicate=True, ignore_links=True, ignore_permissions=True)
        print(f"  Retro: {retro_data['title']}")

def seed_meetings():
    project = _get_project()

    meetings_data = [
        {
            "title": "Sprint Planning — Week 2",
            "project": project,
            "date": add_days(today(), -3),
            "duration": 60,
            "organizer": "rajesh@demo.com",
            "status": "Completed",
            "agenda": "1. Review sprint goal\n2. Assign stories\n3. Discuss dependencies\n4. Capacity check",
            "notes": "Team committed to 48 story points. One team member on leave.",
        },
        {
            "title": "Architecture Review — Dependency Graph Feature",
            "project": project,
            "date": add_days(today(), -1),
            "duration": 45,
            "organizer": "priya@demo.com",
            "status": "Completed",
            "agenda": "Review proposed DAG structure for dependency map feature.",
            "notes": "Decided to use adjacency list model. Supports up to 10K nodes.",
        },
        {
            "title": "Weekly Standup",
            "project": project,
            "date": today(),
            "duration": 15,
            "organizer": "rajesh@demo.com",
            "status": "Scheduled",
            "agenda": "Quick round-robin updates.",
            "notes": "",
        },
    ]

    for md in meetings_data:
        meeting = frappe.get_doc({"doctype": "Pulse Meeting", **md})
        meeting.flags.ignore_permissions = True
        meeting.flags.ignore_links = True
        for u in DEMO_USERS[:4]:
            meeting.append("attendees", {"user": u})
        meeting.insert(ignore_if_duplicate=True, ignore_links=True, ignore_permissions=True)
        print(f"  Meeting: {md['title']}")

    decisions = [
        ("Architecture Review — Dependency Graph Feature",
         "Use adjacency list model for dependency graph storage",
         "Best query performance for expected data volume.",
         "priya@demo.com", "Active"),
        ("Sprint Planning — Week 2",
         "Reduce sprint scope from 55 to 48 story points",
         "Team capacity lower due to leave.",
         "rajesh@demo.com", "Active"),
    ]

    for meeting_title, decision, rationale, decided_by, status in decisions:
        meeting = frappe.get_all("Pulse Meeting", filters={"title": meeting_title}, pluck="name")
        if meeting:
            _make("Pulse Decision", {
                "meeting": meeting[0],
                "project": project,
                "decision": decision,
                "rationale": rationale,
                "decided_by": decided_by,
                "date": add_days(today(), -2),
                "status": status,
            })
            print(f"  Decision: {decision[:50]}...")

def seed_resources():
    project = _get_project()

    allocations = [
        ("amit@demo.com", 100, "Active"),
        ("deepa@demo.com", 100, "Active"),
        ("vikram@demo.com", 80, "Active"),
        ("neha@demo.com", 100, "Active"),
        ("arjun@demo.com", 50, "Active"),
        ("sara@demo.com", 60, "Active"),
        ("priya@demo.com", 100, "Active"),
        ("rajesh@demo.com", 100, "Active"),
    ]

    for user, alloc, status in allocations:
        _make("Pulse Allocation", {
            "user": user,
            "project": project,
            "allocation_percentage": alloc,
            "status": status,
            "start_date": add_days(today(), -30),
            "end_date": add_days(today(), 60),
        })
        print(f"  Allocation: {user} @ {alloc}%")

    leaves = [
        ("amit@demo.com", "Vacation", add_days(today(), 5), add_days(today(), 7), "Planned"),
        ("neha@demo.com", "Personal", add_days(today(), 10), add_days(today(), 10), "Planned"),
        ("vikram@demo.com", "Sick", add_days(today(), -2), today(), "Approved"),
    ]

    for user, ltype, sdate, edate, status in leaves:
        _make("Pulse Leave", {
            "user": user,
            "leave_type": ltype,
            "start_date": sdate,
            "end_date": edate,
            "status": status,
        })
        print(f"  Leave: {user} ({ltype})")

def seed_portfolio():
    project = _get_project()

    portfolio = frappe.get_doc({
        "doctype": "Pulse Portfolio",
        "portfolio_name": "Flagship Products",
        "description": "Core product portfolio covering Pulse and integrations.",
    })
    portfolio.flags.ignore_permissions = True
    portfolio.flags.ignore_links = True
    portfolio.append("projects", {"project": project})
    portfolio.insert(ignore_if_duplicate=True, ignore_links=True, ignore_permissions=True)
    print(f"  Portfolio: Flagship Products")

    health_data = [
        (add_days(today(), -7), 75, 80, 70, 65, 60, "Yellow"),
        (add_days(today(), -14), 80, 85, 75, 70, 55, "Yellow"),
    ]

    for cdate, sched, budget, quality, team, risk, health in health_data:
        _make("Pulse Health Check", {
            "project": project,
            "check_date": cdate,
            "schedule_score": sched,
            "budget_score": budget,
            "quality_score": quality,
            "team_score": team,
            "risk_score": risk,
            "overall_health": health,
            "notes": f"Schedule on track ({sched}%). Budget concerns remain.",
        })
        print(f"  Health Check: {cdate} — {health}")

def seed_changes():
    project = _get_project()
    tasks = _get_tasks()

    cr_list = [
        {
            "title": "Add real-time notification push",
            "project": project,
            "status": "Approved",
            "priority": "High",
            "proposed_by": "amit@demo.com",
            "date": add_days(today(), -10),
            "description": "Replace polling with WebSocket push for instant updates.",
            "reason": "Users reporting 30-second delay in notifications.",
            "impact_on_schedule": 5,
            "impact_on_budget": 8000,
            "impact_on_scope": "Adds WebSocket server. Frontend changes.",
            "decision": "Approved with reduced scope for MVP.",
            "decided_by": "priya@demo.com",
            "decision_date": add_days(today(), -8),
        },
        {
            "title": "Support dark mode in Pulse UI",
            "project": project,
            "status": "Under Review",
            "priority": "Medium",
            "proposed_by": "sara@demo.com",
            "date": add_days(today(), -3),
            "description": "System-preference-based dark mode toggle.",
            "reason": "40% of surveyed users requested dark mode.",
            "impact_on_schedule": 3,
            "impact_on_budget": 3000,
            "impact_on_scope": "CSS custom properties refactor.",
            "decision": "",
            "decided_by": "",
            "decision_date": None,
        },
        {
            "title": "Export Pulse reports to PDF",
            "project": project,
            "status": "Draft",
            "priority": "Low",
            "proposed_by": "rajesh@demo.com",
            "date": today(),
            "description": "PDF export button for all report views.",
            "reason": "Stakeholders want reports for exec meetings.",
            "impact_on_schedule": 2,
            "impact_on_budget": 1500,
            "impact_on_scope": "PDF generator library. Report layout templates.",
            "decision": "",
            "decided_by": "",
            "decision_date": None,
        },
    ]

    for cd in cr_list:
        cr = frappe.get_doc({"doctype": "Pulse Change Request", **cd})
        cr.flags.ignore_permissions = True
        cr.flags.ignore_links = True
        if cd["status"] == "Approved":
            cr.append("linked_tasks", {"task": tasks[0]})
        cr.insert(ignore_if_duplicate=True, ignore_links=True, ignore_permissions=True)
        print(f"  CR: {cd['title']} ({cd['status']})")

        if cd["status"] == "Approved":
            _make("Pulse CR Approval", {
                "change_request": cr.name,
                "approver": "priya@demo.com",
                "status": "Approved",
                "comment": "Approved with reduced scope.",
                "date": add_days(today(), -8),
            })

def seed_dependencies():
    tasks = _get_tasks()
    if len(tasks) < 10:
        return

    deps = [
        (tasks[0], tasks[1], "Finish-to-Start", 0, "Active"),
        (tasks[2], tasks[3], "Finish-to-Start", 1, "Active"),
        (tasks[4], tasks[5], "Start-to-Start", 0, "Active"),
        (tasks[6], tasks[7], "Finish-to-Start", 0, "Resolved"),
        (tasks[8], tasks[9], "Finish-to-Finish", 0, "Active"),
    ]

    for src, tgt, dtype, lag, status in deps:
        _make("Pulse Dependency", {
            "source_task": src,
            "target_task": tgt,
            "dependency_type": dtype,
            "lag_days": lag,
            "status": status,
        })
        print(f"  Dep: {_get_task_subject(src)[:40]} → {_get_task_subject(tgt)[:40]} ({dtype})")

def seed_timesheets():
    tasks = _get_tasks()
    project = _get_project()

    for user in ["amit@demo.com", "deepa@demo.com"]:
        for week_offset in range(2):
            week_starting = add_days(today(), -14 + week_offset * 7)

            ts = frappe.get_doc({
                "doctype": "Pulse Timesheet",
                "user": user,
                "week_starting": week_starting,
                "status": "Approved" if week_offset == 0 else "Draft",
                "total_hours": 0,
            })
            ts.flags.ignore_permissions = True
            ts.flags.ignore_links = True

            total = 0
            for day in range(5):
                day_date = add_days(week_starting, day)
                if tasks:
                    for _ in range(random.randint(1, 2)):
                        task = random.choice(tasks)
                        hours = round(random.uniform(1.5, 4), 1)
                        total += hours
                        ts.append("entries", {
                            "date": day_date,
                            "task": task,
                            "project": project,
                            "hours": hours,
                            "billable": 1,
                            "activity_type": random.choice(["Development", "Meeting", "Design", "Research", "Testing"]),
                            "description": _get_task_subject(task)[:100],
                        })

            ts.insert(ignore_if_duplicate=True, ignore_links=True, ignore_permissions=True)
            frappe.db.set_value("Pulse Timesheet", ts.name, "total_hours", round(total, 1))
            print(f"  Timesheet: {user} ({week_starting}) — {round(total, 1)}h")

def run():
    print("Seeding all Pulse features...\n")

    print("1. OKRs & Key Results...")
    seed_okrs()

    print("\n2. Risks...")
    seed_risks()

    print("\n3. Retrospectives...")
    seed_retros()

    print("\n4. Meetings & Decisions...")
    seed_meetings()

    print("\n5. Resource Allocations & Leave...")
    seed_resources()

    print("\n6. Portfolio & Health Checks...")
    seed_portfolio()

    print("\n7. Change Requests...")
    seed_changes()

    print("\n8. Dependencies...")
    seed_dependencies()

    print("\n9. Timesheets...")
    seed_timesheets()

    print("\n✓ All features seeded successfully!")
