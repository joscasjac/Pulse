import frappe
from frappe.utils import add_days, getdate, now_datetime, flt
from random import randint, choice, seed as set_seed

set_seed(42)

PASSWORD = "Pulse@1234"

USERS = [
    {"email": "rajesh@demo.com",  "first_name": "Rajesh",  "last_name": "Sharma",    "role": "Pulse Admin",       "title": "Product Manager"},
    {"email": "priya@demo.com",   "first_name": "Priya",   "last_name": "Patel",     "role": "Pulse Manager",     "title": "Engineering Lead"},
    {"email": "amit@demo.com",    "first_name": "Amit",    "last_name": "Singh",     "role": "Pulse Team Lead",   "title": "Senior Frontend Engineer"},
    {"email": "deepa@demo.com",   "first_name": "Deepa",   "last_name": "Venkatesh", "role": "Pulse Senior Developer", "title": "Senior Backend Engineer"},
    {"email": "vikram@demo.com",  "first_name": "Vikram",  "last_name": "Joshi",     "role": "Pulse Senior Developer", "title": "Backend Engineer"},
    {"email": "neha@demo.com",    "first_name": "Neha",    "last_name": "Gupta",     "role": "Pulse Junior Developer", "title": "Frontend Engineer"},
    {"email": "arjun@demo.com",   "first_name": "Arjun",   "last_name": "Nair",      "role": "Pulse Junior Developer", "title": "Junior Developer"},
    {"email": "sara@demo.com",    "first_name": "Sara",    "last_name": "Khan",      "role": "Pulse Senior Developer", "title": "Designer"},
]

def run():
    today = getdate()
    users = _create_users()
    project = _create_project(users)
    sprints = _create_sprints(today, project)
    _create_tasks(project, sprints, users, today)
    print("\n=== PULSE DEMO SEEDED ===")
    print(f"Project: {project.name}")
    print(f"Members: {len(users)}")
    for u in users:
        print(f"  {u.first_name} {u.last_name} ({u.email}) — {u.get('title', u.roles[0].role if u.roles else '')}")
    print(f"\nLogin: any @demo.com / {PASSWORD}")

def _create_users():
    created = []
    for u in USERS:
        if frappe.db.exists("User", u["email"]):
            user = frappe.get_doc("User", u["email"])
            created.append(user)
            continue
        user = frappe.get_doc({
            "doctype": "User",
            "email": u["email"],
            "first_name": u["first_name"],
            "last_name": u["last_name"],
            "send_welcome_email": 0,
            "new_password": PASSWORD,
            "roles": [{"role": u["role"]}],
        })
        user.insert(ignore_permissions=True)
        created.append(user)
    frappe.db.commit()
    return created

def _create_project(users):
    name = "Pulse"
    existing = frappe.db.get_value("Pulse Project", {"project_name": name})
    if existing:
        proj = frappe.get_doc("Pulse Project", existing)
        _ensure_team(proj, users)
        return proj
    proj = frappe.get_doc({
        "doctype": "Pulse Project",
        "project_name": name,
        "status": "Open",
        "pulse_enable_scrum": 1,
        "pulse_board_type": "Scrum",
        "pulse_default_sprint_length": 14,
        "pulse_project_key": "PULSE",
    })
    proj.insert(ignore_permissions=True)
    _ensure_team(proj, users)
    frappe.db.commit()
    return proj

def _ensure_team(proj, users):
    for u in users:
        exists = any(row.user == u.email for row in proj.users)
        if not exists:
            proj.append("users", {
                "user": u.email,
                "role": _get_user_role(u),
                "is_lead": 1 if u.email == "rajesh@demo.com" else 0,
            })
    proj.save(ignore_permissions=True)

def _get_user_role(user):
    for r in getattr(user, "roles", []):
        role = r.role if isinstance(r, frappe.model.document.Document) else r.get("role")
        if role.startswith("Pulse"):
            return role
    return "Pulse Junior Developer"

def _create_sprints(today, project):
    sprints = []
    sprint_data = [
        ("Sprint 1",  add_days(today, -55), add_days(today, -41), "Completed", 42, 38),
        ("Sprint 2",  add_days(today, -40), add_days(today, -26), "Completed", 38, 35),
        ("Sprint 3",  add_days(today, -25), add_days(today, -11), "Completed", 45, 42),
        ("Sprint 4 (Active)", add_days(today, -10), add_days(today, 4), "Active", 34, 18),
    ]
    for name, sd, ed, status, planned, completed in sprint_data:
        if frappe.db.exists("Pulse Sprint", name):
            sprints.append(frappe.get_doc("Pulse Sprint", name))
            continue
        sprint = frappe.get_doc({
            "doctype": "Pulse Sprint",
            "sprint_name": name,
            "project": project.name,
            "start_date": sd,
            "end_date": ed,
            "status": status,
            "planned_points": planned,
            "completed_points": completed,
        })
        sprint.insert(ignore_permissions=True)
        sprints.append(sprint)
    frappe.db.commit()
    return sprints

EPICS = [
    {"subject": "User Authentication & SSO",     "key": "PULSE-001"},
    {"subject": "Dashboard & Analytics",          "key": "PULSE-002"},
    {"subject": "Sprint Planning Engine",         "key": "PULSE-003"},
    {"subject": "Kanban Board UX",                "key": "PULSE-004"},
    {"subject": "Notifications & Webhooks",       "key": "PULSE-005"},
    {"subject": "Team Management & Permissions",  "key": "PULSE-006"},
]

TASKS = [
    # Epic 1: User Authentication & SSO
    ("PULSE-007", "Design login/signup flow",                                        "Done",      5, 0, "rajesh@demo.com", 0, "User Authentication & SSO"),
    ("PULSE-008", "Implement OAuth2 provider integrations (Google, GitHub)",          "Done",      8, 0, "deepa@demo.com",   0, "User Authentication & SSO"),
    ("PULSE-009", "Build SAML/SSO login page",                                        "Done",      5, 0, "neha@demo.com",    0, "User Authentication & SSO"),
    ("PULSE-010", "Add passwordless magic-link auth",                                 "Done",      3, 0, "deepa@demo.com",   0, "User Authentication & SSO"),
    ("PULSE-011", "Create user session management API",                               "Done",      5, 1, "vikram@demo.com",  0, "User Authentication & SSO"),
    ("PULSE-012", "Implement role-based access control (RBAC) middleware",            "Done",      8, 1, "deepa@demo.com",   1, "User Authentication & SSO"),
    ("PULSE-013", "Build two-factor authentication UI",                               "In Review", 5, 3, "neha@demo.com",    1, "User Authentication & SSO"),
    ("PULSE-014", "Add API key management for integrations",                          "In Progress", 3, 3, "vikram@demo.com",  1, "User Authentication & SSO"),

    # Epic 2: Dashboard & Analytics
    ("PULSE-015", "Design dashboard data model and aggregation pipeline",             "Done",      8, 0, "priya@demo.com",   0, "Dashboard & Analytics"),
    ("PULSE-016", "Build burndown chart component (SVG)",                             "Done",      5, 1, "amit@demo.com",    0, "Dashboard & Analytics"),
    ("PULSE-017", "Create velocity trend chart with moving average",                  "Done",      5, 1, "amit@demo.com",    0, "Dashboard & Analytics"),
    ("PULSE-018", "Implement cumulative flow diagram",                                "Done",      5, 1, "deepa@demo.com",   0, "Dashboard & Analytics"),
    ("PULSE-019", "Build cycle-time scatter plot (percentile view)",                  "Done",      5, 2, "amit@demo.com",    0, "Dashboard & Analytics"),
    ("PULSE-020", "Add dashboard date-range picker and filters",                      "Done",      3, 2, "neha@demo.com",    0, "Dashboard & Analytics"),
    ("PULSE-021", "Create exportable sprint report (PDF)",                            "In Review", 5, 3, "arjun@demo.com",   1, "Dashboard & Analytics"),
    ("PULSE-022", "Add workload histogram by team member",                            "In Progress", 5, 3, "deepa@demo.com",  1, "Dashboard & Analytics"),
    ("PULSE-023", "Build real-time dashboard refresh via WebSocket",                  "To Do",     8, 3, "vikram@demo.com",  1, "Dashboard & Analytics"),

    # Epic 3: Sprint Planning Engine
    ("PULSE-024", "Design sprint data model and state machine",                       "Done",      5, 0, "priya@demo.com",   0, "Sprint Planning Engine"),
    ("PULSE-025", "Implement sprint create/close/complete lifecycle",                 "Done",      5, 0, "deepa@demo.com",   0, "Sprint Planning Engine"),
    ("PULSE-026", "Build drag-to-sprint backlog grooming UI",                         "Done",      8, 1, "amit@demo.com",    0, "Sprint Planning Engine"),
    ("PULSE-027", "Add story-point estimation poker (consensus tool)",                "Done",      5, 2, "amit@demo.com",    1, "Sprint Planning Engine"),
    ("PULSE-028", "Implement automatic sprint goal tracking",                         "In Progress", 3, 3, "priya@demo.com",   1, "Sprint Planning Engine"),
    ("PULSE-029", "Build sprint capacity planner (FTE × days)",                      "To Do",      5, 3, "deepa@demo.com",   1, "Sprint Planning Engine"),

    # Epic 4: Kanban Board UX
    ("PULSE-030", "Design column-based Kanban layout with drag-drop",                 "Done",      8, 0, "sara@demo.com",    0, "Kanban Board UX"),
    ("PULSE-031", "Build real-time card position sync via API",                       "Done",      5, 1, "vikram@demo.com",  0, "Kanban Board UX"),
    ("PULSE-032", "Implement WIP-limit enforcement on columns",                       "Done",      3, 2, "deepa@demo.com",   1, "Kanban Board UX"),
    ("PULSE-033", "Add quick-card creation with inline editing",                      "Done",      5, 2, "neha@demo.com",    1, "Kanban Board UX"),
    ("PULSE-034", "Build swimlane view (by assignee)",                                "In Review", 5, 3, "amit@demo.com",    1, "Kanban Board UX"),
    ("PULSE-035", "Add card detail modal with comments and history",                  "In Progress", 8, 3, "arjun@demo.com",   1, "Kanban Board UX"),
    ("PULSE-036", "Create board-filter by epic/priority/assignee",                    "To Do",      5, 3, "neha@demo.com",    1, "Kanban Board UX"),

    # Epic 5: Notifications & Webhooks
    ("PULSE-037", "Design notification schema and delivery queue",                    "Done",      5, 2, "priya@demo.com",   0, "Notifications & Webhooks"),
    ("PULSE-038", "Build in-app notification bell with read tracking",                "Done",      5, 2, "neha@demo.com",    0, "Notifications & Webhooks"),
    ("PULSE-039", "Implement email notification digest",                              "Done",      3, 2, "vikram@demo.com",  0, "Notifications & Webhooks"),
    ("PULSE-040", "Create webhook endpoint with retry logic",                         "In Progress", 5, 3, "deepa@demo.com",   1, "Notifications & Webhooks"),
    ("PULSE-041", "Add Slack/MS Teams integration for task updates",                  "To Do",      8, 3, "vikram@demo.com",  1, "Notifications & Webhooks"),
    ("PULSE-042", "Build webhook delivery log with replay",                           "To Do",      3, 3, "arjun@demo.com",   1, "Notifications & Webhooks"),

    # Epic 6: Team Management & Permissions
    ("PULSE-043", "Design team hierarchy and project membership model",               "Done",      5, 1, "rajesh@demo.com",  0, "Team Management & Permissions"),
    ("PULSE-044", "Build invite-to-project flow with role selection",                 "Done",      5, 2, "amit@demo.com",    0, "Team Management & Permissions"),
    ("PULSE-045", "Implement granular permission sets (read/write/admin)",            "In Review", 8, 3, "deepa@demo.com",   1, "Team Management & Permissions"),
    ("PULSE-046", "Add activity audit log for project changes",                       "In Progress", 3, 3, "arjun@demo.com",   1, "Team Management & Permissions"),
    ("PULSE-047", "Create team availability calendar",                                "To Do",      5, 3, "neha@demo.com",    1, "Team Management & Permissions"),
]

def _get_user_by_email(email, users):
    for u in users:
        if u.email == email:
            return u
    return users[0]

def _create_tasks(project, sprints, users, today):
    epic_docs = {}
    epic_idx = 1
    for ep in EPICS:
        e = frappe.get_doc({
            "doctype": "Pulse Task",
            "subject": ep["subject"],
            "project": project.name,
            "status": "Completed" if ep["subject"] != "Notifications & Webhooks" else "Open",
            "pulse_story_points": 0,
            "is_milestone": 0,
            "priority": "Medium",
        })
        e.flags.ignore_links = True
        e.insert(ignore_permissions=True)
        epic_docs[ep["subject"]] = e.name

    for idx, (key, subj, state, pts, sprint_off, email, epic_idx, epic_name) in enumerate(TASKS):
        user = _get_user_by_email(email, users)
        sprint = sprints[min(sprint_off, len(sprints) - 1)]
        assignees = [user.email]
        task = frappe.get_doc({
            "doctype": "Pulse Task",
            "subject": subj,
            "project": project.name,
            "status": state if state in ("Open", "Working", "Completed", "Cancelled") else "Open",
            "pulse_sprint": sprint.name,
            "pulse_story_points": pts,
            "pulse_epic": epic_docs[epic_name],
            "pulse_rank": idx * 100,
            "priority": choice(["Low", "Medium", "Medium", "High"]),
            "exp_start_date": add_days(getdate(sprint.start_date), randint(0, 3)),
            "exp_end_date": add_days(getdate(sprint.end_date), -randint(0, 3)) if state == "Done" else getdate(sprint.end_date),
            "_assign": frappe.as_json(assignees),
        })
        task.flags.ignore_links = True
        task.insert(ignore_permissions=True)

        if state in ("Done", "In Review", "In Progress", "Working"):
            frappe.db.set_value("Pulse Task", task.name, "status", state, update_modified=False)

    frappe.db.commit()
