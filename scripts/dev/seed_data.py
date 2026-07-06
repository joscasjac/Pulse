import frappe
from frappe.utils import nowdate, add_days
import random

random.seed(42)

TASK_NAMES = [
    "Set up CI/CD pipeline",
    "Implement user authentication",
    "Design database schema",
    "Create REST API endpoints",
    "Build login page",
    "Add password reset flow",
    "Implement OAuth2 integration",
    "Set up error monitoring",
    "Configure logging framework",
    "Write unit tests for auth module",
    "Create API documentation",
    "Set up staging environment",
    "Configure SSL certificates",
    "Implement rate limiting",
    "Build notification service",
    "Add email templates",
    "Implement file upload",
    "Create search functionality",
    "Build admin dashboard",
    "Add pagination to lists",
    "Implement sorting and filtering",
    "Create export feature",
    "Build CSV import tool",
    "Add data validation",
    "Implement caching layer",
    "Set up CDN",
    "Configure database indexes",
    "Optimize slow queries",
    "Add database replication",
    "Implement backup strategy",
    "Build health check endpoint",
    "Add metrics collection",
    "Create Grafana dashboard",
    "Set up alerting rules",
    "Configure log rotation",
    "Implement audit trail",
    "Add role-based access control",
    "Build permission manager",
    "Implement feature flags",
    "Create A/B test framework",
    "Build onboarding wizard",
    "Add tooltip system",
    "Implement drag-and-drop",
    "Create kanban board",
    "Build calendar view",
    "Add Gantt chart",
    "Implement real-time updates",
    "Add WebSocket support",
    "Create mobile responsive layout",
    "Add dark mode",
    "Implement keyboard shortcuts",
    "Build command palette",
    "Add multi-language support",
    "Create locale files",
    "Implement timezone handling",
    "Build date picker component",
    "Create rich text editor",
    "Add markdown support",
    "Implement @mentions",
    "Add emoji picker",
    "Build activity feed",
    "Create notification preferences",
    "Implement webhook system",
    "Add API key management",
    "Build webhook delivery log",
    "Create rate limit dashboard",
    "Implement IP whitelisting",
    "Add two-factor auth",
    "Build session management",
    "Create login history",
    "Implement SSO/SAML",
    "Add LDAP integration",
    "Build user profile page",
    "Create avatar upload",
    "Implement user search",
    "Add team management UI",
    "Build invite system",
    "Create email verification",
    "Implement billing integration",
    "Add subscription management",
    "Build invoice generation",
    "Create payment method UI",
    "Implement refund flow",
    "Add usage tracking",
    "Build analytics pipeline",
    "Create report scheduler",
    "Implement data retention policy",
    "Add data anonymization",
    "Build export audit log",
    "Create compliance report",
    "Implement SLA tracking",
    "Add uptime monitoring",
    "Build status page",
    "Create incident timeline",
    "Implement postmortem template",
    "Add runbook viewer",
    "Build service catalog",
    "Create dependency graph",
    "Implement cost tracking",
    "Add budget alerting",
]

STATUSES = ["Open", "Working", "Pending Review", "Completed"]

def create_projects(count=10):
    created = []
    for i in range(count):
        name = f"Seed Project {i + 1}"
        if frappe.db.exists("Pulse Project", {"project_name": name}):
            created.append(frappe.db.get_value("Pulse Project", {"project_name": name}))
            continue
        proj = frappe.new_doc("Pulse Project")
        proj.project_name = name
        proj.status = random.choice(["Open", "Open", "Open", "Completed"])
        proj.pulse_enable_scrum = 1
        proj.pulse_board_type = random.choice(["Scrum", "Kanban"])
        proj.insert(ignore_permissions=True)
        created.append(proj.name)
    return created


def create_tasks(project_names, count_per_project=10):
    for proj in project_names:
        existing = frappe.db.count("Pulse Task", {"project": proj})
        if existing >= count_per_project:
            continue
        for i in range(count_per_project):
            task = frappe.new_doc("Pulse Task")
            task.subject = random.choice(TASK_NAMES)
            task.project = proj
            task.status = random.choice(STATUSES)
            task.priority = random.choice(["Low", "Medium", "High", "Urgent"])
            task.exp_start_date = add_days(nowdate(), -random.randint(0, 30))
            task.exp_end_date = add_days(nowdate(), random.randint(15, 120))
            task.pulse_story_points = random.choice([1, 2, 3, 5, 8, 13])
            task.pulse_rank = i * 100
            task.insert(ignore_permissions=True)


def main():
    frappe.flags.ignore_permissions = True
    frappe.db.set_default("ignore_permissions", 1)

    projects = create_projects(10)
    create_tasks(projects, 10)
    frappe.db.commit()
    print(f"Seeded {len(projects)} Pulse Projects with Pulse Tasks.")


if __name__ == "__main__":
    main()
