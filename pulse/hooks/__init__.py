app_name = "pulse"
app_title = "Pulse"
app_publisher = "Frappe"
app_description = "Modern agile delivery layer on top of ERPNext Projects"
required_apps = ["erpnext"]
app_email = "info@frappe.io"
app_icon = "octicon octicon-project"
app_color = "blue"
app_logo_url = "/assets/pulse/images/pulse-logo.png"
app_version = "0.2.0"

# Tiny Desk helper: makes the "Pulse" workspace icon open the SPA at /pulse directly.
app_include_js = ["/assets/pulse/js/pulse_desk.js"]
app_include_css = []

web_include_js = []
web_include_css = []

doctype_js = {}

# ---------------------------------------------------------------------------
# App launcher — show Pulse in Frappe's /apps grid and land users in the SPA
# ---------------------------------------------------------------------------
add_to_apps_screen = [
    {
        "name": "pulse",
        "logo": "/assets/pulse/images/pulse-logo.png",
        "title": "Pulse",
        "route": "/pulse",
        "has_permission": "pulse.api.spa.check_app_permission",
    }
]

on_session_creation = "pulse.api.spa.land_on_pulse"

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
after_install = "pulse.install.after_install"
after_migrate = "pulse.install.after_migrate"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
fixtures = [
    {"dt": "Role", "filters": [["role_name", "like", "Pulse %"]]},
    {"dt": "Task Type"},
    {
        "dt": "Report",
        "filters": [
            [
                "name",
                "in",
                [
                    "Pulse Velocity",
                    "Pulse Burndown",
                    "Pulse Workload",
                    "Pulse Sprint Report",
                    "Pulse Burnup",
                    "Pulse Cumulative Flow",
                    "Pulse Cycle Time",
                    "Pulse Lead Time",
                ],
            ]
        ],
    },
    {
        "dt": "Dashboard Chart",
        "filters": [
            [
                "name",
                "in",
                [
                    "Pulse Sprint Burndown",
                    "Pulse Velocity",
                    "Pulse Workload by Assignee",
                    "Pulse Sprint Burnup",
                    "Pulse Cumulative Flow",
                    "Pulse Cycle Time",
                    "Pulse Lead Time",
                    "Tasks by State",
                ],
            ]
        ],
    },
    {
        "dt": "Number Card",
        "filters": [
            [
                "name",
                "in",
                [
                    "Active Sprint Points",
                    "Overdue Tasks",
                    "Open Tasks",
                    "My Open Tasks",
                    "In Review Count",
                    "Sprint Completed %",
                    "Spillover Task Count",
                    "My Hours Logged This Week",
                    "Avg Velocity",
                    "Billable Hours This Month",
                    "Avg Cycle Time",
                ],
            ]
        ],
    },
]

# ---------------------------------------------------------------------------
# Vue SPA (frontend) — serve built app at /pulse and route deep links to it
# ---------------------------------------------------------------------------
website_route_rules = [
    {"from_route": "/pulse/<path:app_path>", "to_route": "pulse"},
]

# ---------------------------------------------------------------------------
# Document Events
# ---------------------------------------------------------------------------
doc_events = {
    "Task": {
        "before_insert": "pulse.hooks.events.task.before_insert",
        "on_update": ["pulse.hooks.events.task.on_update", "pulse.api.sprint_history.record_task_change"],
        "on_trash": "pulse.api.sprint_history.record_task_deletion",
        "validate": ["pulse.hooks.permissions.validate_task_assignees", "pulse.hooks.permissions.validate_scope"],
    },
    "ToDo": {
        "validate": "pulse.hooks.permissions.on_todo_assign",
        "after_insert": "pulse.api.notify.on_todo_after_insert",
    },
}

# ---------------------------------------------------------------------------
# Row-level visibility for core Task/Project/Pulse doctypes
# ---------------------------------------------------------------------------
permission_query_conditions = {
    "Task": "pulse.hooks.permissions.task_query_conditions",
    "Pulse Sprint": "pulse.hooks.permissions.sprint_query_conditions",
    "Pulse Task Status Log": "pulse.hooks.permissions.status_log_query_conditions",
}

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
scheduler_events = {
    "daily": [
        "pulse.scheduled.reminders.send_advance_reminders",
        "pulse.scheduled.overdue.flag_overdue_tasks",
        "pulse.scheduled.sprints.auto_close_sprints",
        "pulse.scheduled.metrics.snapshot_burndown",
        "pulse.scheduled.recurring.generate_due",
    ],
    "hourly": [
        "pulse.scheduled.project_cache.refresh_project_stats",
    ],
}


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
boot_session = "pulse.hooks.bootinfo.extend_bootinfo"

# Apply the same membership boundary to REST documents and permission-aware lists.
from pulse.hooks.permissions import TASK_LINKS
has_permission = {
    "Task": "pulse.hooks.permissions.task_has_permission",
    "Project": "pulse.hooks.permissions.project_has_permission",
}
permission_query_conditions["Project"] = "pulse.hooks.permissions.project_query_conditions"
permission_query_conditions['Pulse Comment'] = "pulse.hooks.permissions.pulse_comment_query"
has_permission['Pulse Comment'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Activity Log'] = "pulse.hooks.permissions.pulse_activity_log_query"
has_permission['Pulse Activity Log'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Allocation'] = "pulse.hooks.permissions.pulse_allocation_query"
has_permission['Pulse Allocation'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Task Status Log'] = "pulse.hooks.permissions.pulse_task_status_log_query"
has_permission['Pulse Task Status Log'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Risk'] = "pulse.hooks.permissions.pulse_risk_query"
has_permission['Pulse Risk'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Goal'] = "pulse.hooks.permissions.pulse_goal_query"
has_permission['Pulse Goal'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Document'] = "pulse.hooks.permissions.pulse_document_query"
has_permission['Pulse Document'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Sprint'] = "pulse.hooks.permissions.pulse_sprint_query"
has_permission['Pulse Sprint'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Recurring Task'] = "pulse.hooks.permissions.pulse_recurring_task_query"
has_permission['Pulse Recurring Task'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Change Request'] = "pulse.hooks.permissions.pulse_change_request_query"
has_permission['Pulse Change Request'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Retrospective'] = "pulse.hooks.permissions.pulse_retrospective_query"
has_permission['Pulse Retrospective'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Decision'] = "pulse.hooks.permissions.pulse_decision_query"
has_permission['Pulse Decision'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Meeting'] = "pulse.hooks.permissions.pulse_meeting_query"
has_permission['Pulse Meeting'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Checklist'] = "pulse.hooks.permissions.pulse_checklist_query"
has_permission['Pulse Checklist'] = "pulse.hooks.permissions.scoped_has_permission"
permission_query_conditions['Pulse Dependency'] = "pulse.hooks.permissions.pulse_dependency_query"
has_permission['Pulse Dependency'] = "pulse.hooks.permissions.scoped_has_permission"

permission_query_conditions["Timesheet"] = "pulse.hooks.permissions.timesheet_query_conditions"
has_permission["Timesheet"] = "pulse.hooks.permissions.timesheet_has_permission"

for _scoped_doctype in has_permission:
    if _scoped_doctype not in ("Task", "Project", "Timesheet"):
        doc_events.setdefault(_scoped_doctype, {})["validate"] = "pulse.hooks.permissions.validate_scope"

doc_events["Timesheet"] = {"validate": "pulse.hooks.permissions.validate_timesheet"}
doc_events["Pulse Timesheet"] = {
    "validate": "pulse.hooks.permissions.freeze_legacy_timesheet",
    "on_trash": "pulse.hooks.permissions.freeze_legacy_timesheet",
}
doc_events["Task"]["on_trash"] = ["pulse.hooks.permissions.protect_task_time", "pulse.api.sprint_history.record_task_deletion"]
after_migrate = ["pulse.install.after_migrate", "pulse.api.sprint_history.initialize_active_history"]

permission_query_conditions["Pulse Notification"] = "pulse.hooks.permissions.notification_query_conditions"
has_permission["Pulse Notification"] = "pulse.hooks.permissions.notification_has_permission"
permission_query_conditions["Pulse Dashboard"] = "pulse.hooks.permissions.dashboard_query_conditions"
has_permission["Pulse Dashboard"] = "pulse.hooks.permissions.dashboard_has_permission"

# Map project vocabulary before ERPNext validates completion/dependencies/progress.
doc_events["Task"]["before_validate"] = [
    "pulse.hooks.permissions.preserve_private_task_links",
    "pulse.api.task_config.validate_task",
]
doc_events.setdefault("Project", {})["validate"] = ["pulse.api.task_config.validate_project_config", "pulse.api.business.validate_project_business"]
doc_events["Pulse Label"] = {"validate": "pulse.api.task_config.validate_label"}
permission_query_conditions["Pulse Label"] = "pulse.hooks.permissions.pulse_label_query"
has_permission["Pulse Label"] = "pulse.hooks.permissions.scoped_has_permission"

doc_events["ToDo"]["after_insert"] = ["pulse.api.notify.on_todo_after_insert", "pulse.api.tasks.record_assignment"]
doc_events["ToDo"]["on_update"] = "pulse.api.tasks.record_assignment"

# Request intake uses the same project scope as the accepted work.
permission_query_conditions["Pulse Request"] = "pulse.api.intake.query_conditions"
has_permission["Pulse Request"] = "pulse.api.intake.has_permission"
after_migrate.append("pulse.api.task_config.initialize_project_statuses")

permission_query_conditions["Pulse Saved View"] = "pulse.api.views.query_conditions"
has_permission["Pulse Saved View"] = "pulse.api.views.has_permission"

# Personal navigation and inbox records never widen record access.
permission_query_conditions["Pulse Personal Item"] = "pulse.api.personal.personal_query"
has_permission["Pulse Personal Item"] = "pulse.api.personal.personal_permission"
doc_events["Task"]["on_update"].append("pulse.api.personal.task_updated")
doc_events["ToDo"]["after_insert"].append("pulse.api.personal.assignment_created")
doc_events.setdefault("Pulse Comment", {})["after_insert"] = "pulse.api.personal.comment_created"

permission_query_conditions["Pulse Timesheet"] = "pulse.hooks.permissions.legacy_timesheet_query_conditions"
has_permission["Pulse Timesheet"] = "pulse.hooks.permissions.timesheet_has_permission"

doc_events["ToDo"]["on_trash"] = "pulse.api.tasks.record_assignment"

# Native upload, direct File REST and private download inherit the parent scope.
doc_events["File"] = {"before_validate": "pulse.hooks.permissions.validate_private_attachment",
                      "before_insert": "pulse.hooks.permissions.validate_private_attachment"}
has_permission["File"] = "pulse.hooks.permissions.attachment_has_permission"
permission_query_conditions["File"] = "pulse.hooks.permissions.attachment_query_conditions"

extend_doctype_class = {
    "File": ["pulse.hooks.permissions.PrivateAttachmentDownloadMixin"],
    "Task": ["pulse.hooks.permissions.TaskReadScopeMixin"],
}

# Modules group native tasks without exposing membership outside task visibility.
permission_query_conditions['Pulse Module'] = 'pulse.api.modules.query_conditions'
has_permission['Pulse Module'] = 'pulse.api.modules.has_permission'
permission_query_conditions['Pulse Module Task'] = 'pulse.api.modules.membership_query'
has_permission['Pulse Module Task'] = 'pulse.api.modules.membership_permission'
doc_events['Task']['on_update'].append('pulse.api.modules.task_project_changed')
doc_events['Task']['on_update'].append('pulse.api.tasks.refresh_dependency_projects')
doc_events['Task']['on_trash'].append('pulse.api.modules.task_deleted')
