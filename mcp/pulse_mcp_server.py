#!/usr/bin/env python3
"""Pulse MCP server.

Exposes Pulse project-management operations as MCP tools so an AI assistant
(Claude Desktop / Claude Code) can create, edit, move, assign and comment on
tasks, sprints and projects in plain language.

It talks to a running Frappe/Pulse site over the REST API using an API
key + secret (token auth). Nothing here depends on ERPNext.

Environment variables
---------------------
    PULSE_SITE_URL      e.g. http://127.0.0.1:8000   (or your public URL)
    PULSE_API_KEY       User's API key
    PULSE_API_SECRET    User's API secret
    PULSE_SITE_HOST     (optional) Host header, e.g. project.local — needed
                        when the site is served by hostname behind the URL.

Run:  python pulse_mcp_server.py     (stdio transport)
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP


def _load_local_env():
    """Fall back to a .pulse.env file next to this script (KEY=VALUE per line).

    Lets the launch config stay clean (no secrets in Claude config / process args).
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pulse.env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_local_env()

SITE = os.environ.get("PULSE_SITE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("PULSE_API_KEY", "")
API_SECRET = os.environ.get("PULSE_API_SECRET", "")
SITE_HOST = os.environ.get("PULSE_SITE_HOST", "")

mcp = FastMCP("pulse")


def _headers():
    h = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if SITE_HOST:
        h["Host"] = SITE_HOST
    return h


def call(method: str, **params):
    """Call a whitelisted Frappe/Pulse method and return its `message` payload."""
    body = {k: v for k, v in params.items() if v is not None}
    try:
        r = httpx.post(f"{SITE}/api/method/{method}", headers=_headers(),
                       json=body, timeout=30)
    except Exception as e:
        return {"error": f"Cannot reach Pulse at {SITE}: {e}"}
    if r.status_code >= 400:
        # surface Frappe's error message if present
        try:
            data = r.json()
            msg = (data.get("exception") or data.get("_server_messages") or data.get("message") or r.text)
        except Exception:
            msg = r.text
        return {"error": f"HTTP {r.status_code}: {msg}"}
    try:
        return r.json().get("message", r.json())
    except Exception:
        return {"error": r.text}


def _resolve(ref: str) -> str:
    """Turn an issue key like PLS5-3 into the internal task name."""
    res = call("pulse.api.spa.resolve_task", ref=ref)
    return res if isinstance(res, str) else ref


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@mcp.tool()
def list_projects() -> list:
    """List all Pulse projects (name, key, status)."""
    return call("frappe.client.get_list", doctype="Project",
                fields=["name", "project_name", "pulse_project_key", "status"],
                limit_page_length=0)


@mcp.tool()
def list_tasks(project: str = None, status: str = None, assignee: str = None,
               search: str = None, limit: int = 50) -> list:
    """List tasks. Optionally filter by project, status, assignee (email) or a text search."""
    filters = {}
    if project:
        filters["project"] = project
    if status:
        filters["status"] = status
    if assignee:
        filters["_assign"] = ["like", f"%{assignee}%"]
    or_filters = None
    if search:
        or_filters = [["subject", "like", f"%{search}%"], ["issue_key", "like", f"%{search}%"]]
    return call("frappe.client.get_list", doctype="Task",
                fields=["name", "issue_key", "subject", "status", "priority",
                        "type as task_type", "project", "pulse_sprint", "_assign"],
                filters=filters, or_filters=or_filters,
                order_by="modified desc", limit_page_length=int(limit))


@mcp.tool()
def get_task(ref: str) -> dict:
    """Get full detail for a task by its key (e.g. PLS5-3): fields, assignees, sub-tasks, dependencies, comments."""
    return call("pulse.api.spa.get_task", task=_resolve(ref))


@mcp.tool()
def list_sprints(project: str = None) -> list:
    """List sprints, optionally for one project."""
    filters = {"project": project} if project else {}
    return call("frappe.client.get_list", doctype="Pulse Sprint",
                fields=["name", "sprint_name", "status", "start_date", "end_date", "project"],
                filters=filters, limit_page_length=0)


@mcp.tool()
def list_users() -> list:
    """List users the connected account may assign work to (respects the hierarchy rule)."""
    return call("pulse.api.spa.get_assignable_users")


# ---------------------------------------------------------------------------
# Create / edit
# ---------------------------------------------------------------------------

@mcp.tool()
def create_task(project: str, subject: str, description: str = None,
                task_type: str = "Task", priority: str = "Medium",
                state: str = "Backlog", assignees: list = None,
                sprint: str = None, due_date: str = None,
                story_points: float = None) -> dict:
    """Create a task and optionally assign people to it.

    `assignees` is a list of user emails. Assignment obeys the hierarchy rule
    (you can only assign at or below your own level). `state` is one of
    Backlog / To Do / In Progress / In Review / Done.
    """
    return call("pulse.api.spa.create_task", project=project, subject=subject,
                description=description, task_type=task_type, priority=priority,
                state=state, assignees=json.dumps(assignees or []),
                pulse_sprint=sprint, exp_end_date=due_date, pulse_story_points=story_points)


@mcp.tool()
def update_task(ref: str, subject: str = None, description: str = None,
                priority: str = None, task_type: str = None,
                due_date: str = None, story_points: float = None,
                sprint: str = None) -> dict:
    """Edit fields on an existing task (by key). Only provided fields change."""
    fields = {}
    if subject is not None: fields["subject"] = subject
    if description is not None: fields["description"] = description
    if priority is not None: fields["priority"] = priority
    if task_type is not None: fields["task_type"] = task_type
    if due_date is not None: fields["exp_end_date"] = due_date
    if story_points is not None: fields["pulse_story_points"] = story_points
    if sprint is not None: fields["pulse_sprint"] = sprint
    return call("pulse.api.spa.update_task", task=_resolve(ref), **fields)


@mcp.tool()
def move_task(ref: str, state: str) -> dict:
    """Move a task to a board column: Backlog / To Do / In Progress / In Review / Done."""
    return call("pulse.api.spa.update_task_state", task=_resolve(ref), state=state)


@mcp.tool()
def assign_task(ref: str, user: str) -> dict:
    """Assign a user (email) to a task. Blocked if the user is above your level."""
    return call("pulse.api.spa.assign_task", task=_resolve(ref), user=user)


@mcp.tool()
def unassign_task(ref: str, user: str) -> dict:
    """Remove a user's assignment from a task."""
    return call("pulse.api.spa.unassign_task", task=_resolve(ref), user=user)


@mcp.tool()
def add_comment(ref: str, text: str) -> dict:
    """Add a comment to a task."""
    return call("pulse.api.spa.add_comment", task=_resolve(ref), text=text)


@mcp.tool()
def add_subtask(parent_ref: str, subject: str) -> dict:
    """Create a sub-task under a parent task (by key)."""
    return call("pulse.api.spa.add_subtask", parent=_resolve(parent_ref), subject=subject)


@mcp.tool()
def add_dependency(ref: str, blocked_by_ref: str) -> dict:
    """Mark `ref` as blocked by `blocked_by_ref` (both are task keys)."""
    return call("pulse.api.spa.add_dependency",
                task=_resolve(ref), depends_on=_resolve(blocked_by_ref))


@mcp.tool()
def delete_task(ref: str) -> dict:
    """Delete a task by key (also removes its status logs, comments, checklist, dependencies)."""
    return call("pulse.api.spa.delete_task", task=_resolve(ref))


@mcp.tool()
def create_sprint(name: str, project: str, status: str = "Planned",
                  start_date: str = None, end_date: str = None, goal: str = None) -> dict:
    """Create a sprint for a project. status: Planned / Active / Completed."""
    doc = {"doctype": "Pulse Sprint", "sprint_name": name, "project": project,
           "status": status, "start_date": start_date, "end_date": end_date, "goal": goal}
    return call("pulse.api.spa.save_entity", doc=json.dumps(doc))


@mcp.tool()
def create_project(name: str, key: str = None, description: str = None,
                   status: str = "Open") -> dict:
    """Create a new project. `key` becomes the task-id prefix (e.g. OPS)."""
    doc = {"doctype": "Pulse Project", "project_name": name,
           "pulse_project_key": key, "description": description, "status": status}
    return call("pulse.api.spa.save_entity", doc=json.dumps(doc))


if __name__ == "__main__":
    mcp.run()
