"""Project knowledge pages. All access inherits the native project's visibility."""
import frappe
from pulse.hooks.permissions import require_permission

TEMPLATES = {
    "brief": "<h2>Project brief</h2><h3>Outcome</h3><p>What will success look like?</p><h3>Scope</h3><p>Deliverables and exclusions</p><h3>Stakeholders</h3><p>Owners and decision makers</p><h3>Milestones</h3><p>Dates and acceptance criteria</p>",
    "meeting": "<h2>Meeting notes</h2><h3>Agenda</h3><ul><li>Discussion topics</li></ul><h3>Decisions</h3><p>Record decisions and their context</p><h3>Actions</h3><p>Owner, task and due date</p>",
    "specification": "<h2>Specification</h2><h3>Problem</h3><p>Who needs this and why?</p><h3>Requirements</h3><p>Expected behavior and constraints</p><h3>Acceptance criteria</h3><ul><li>Verifiable outcome</li></ul><h3>Open questions</h3><p>Decisions still needed</p>",
}

@frappe.whitelist()
def templates():
    return TEMPLATES

@frappe.whitelist()
def list_pages(project=None, query=None):
    filters = {}
    if project:
        require_permission("Project", project)
        filters["project"] = project
    return frappe.get_list("Pulse Document", filters=filters,
        or_filters={"title": ["like", f"%{query}%"], "content": ["like", f"%{query}%"]} if query else None,
        fields=["name", "title", "project", "modified", "modified_by"], order_by="modified desc", limit_page_length=0)

@frappe.whitelist()
def get_page(name):
    doc = require_permission("Pulse Document", name)
    result = doc.as_dict()
    result.pop("collab_updates", None)
    result["can_write"] = bool(frappe.has_permission("Pulse Document", "write", doc=doc))
    result["comments"] = frappe.get_all("Comment", filters={"reference_doctype": "Pulse Document", "reference_name": name, "comment_type": "Comment"}, fields=["name", "content", "owner", "creation"], order_by="creation asc")
    result["tasks"] = [frappe.get_doc("Task", row.task).as_dict() for row in doc.get("task_links") or [] if frappe.has_permission("Task", "read", doc=row.task)]
    return result

@frappe.whitelist()
def save_page(project, title, content="", name=None, modified=None, tasks=None, template=None, base_details=None):
    require_permission("Project", project)
    if name:
        doc = require_permission("Pulse Document", name, "write")
        # Read the locked row itself, not a non-locking snapshot taken before
        # another writer committed (MariaDB REPEATABLE READ).
        doc = frappe.get_doc("Pulse Document", name, for_update=True)
        if not modified or str(doc.modified) != str(modified):
            frappe.throw("This page changed while you were editing. Reload the latest version before saving.", frappe.TimestampMismatchError)
        if base_details is not None:
            baseline = frappe.parse_json(base_details) if isinstance(base_details, str) else base_details
            if not isinstance(baseline, dict) or baseline.get("title") != doc.title or sorted(baseline.get("tasks") or []) != sorted(row.task for row in doc.get("task_links") or []):
                frappe.throw("Page details changed while you were editing. Reopen the page before changing its title or task links.", frappe.TimestampMismatchError)
        if project != doc.project:
            frappe.throw("A page cannot be moved to another project.")
    else:
        doc = frappe.new_doc("Pulse Document")
        doc.project = project
        if template:
            if template not in TEMPLATES:
                frappe.throw("Unknown page template")
            content = TEMPLATES[template]
    doc.title = title
    # Rich body changes use the CRDT endpoint once collaboration is initialized.
    if not doc.get("collab_updates"):
        doc.content = content
    if tasks is not None:
        task_names = frappe.parse_json(tasks) if isinstance(tasks, str) else tasks
        if not isinstance(task_names, list):
            frappe.throw("Task links must be a list")
        doc.set("task_links", [{"task": task} for task in dict.fromkeys(task_names)])
    doc.save(ignore_version=False)
    return get_page(doc.name)

@frappe.whitelist()
def add_comment(name, content):
    doc = require_permission("Pulse Document", name)
    if not (content or "").strip():
        frappe.throw("Write a comment first")
    from pulse.pulse.doctype.pulse_document.pulse_document import safe_mentions
    doc.add_comment("Comment", safe_mentions(content, doc))
    return get_page(name)

@frappe.whitelist()
def revisions(name):
    require_permission("Pulse Document", name)
    return frappe.get_all("Version", filters={"ref_doctype": "Pulse Document", "docname": name}, fields=["name", "owner", "creation", "data"], order_by="creation desc", limit_page_length=100)

@frappe.whitelist()
def task_pages(task):
    require_permission("Task", task)
    names = frappe.get_all("Pulse Document Task", filters={"task": task, "parenttype": "Pulse Document"}, pluck="parent")
    return frappe.get_list("Pulse Document", filters={"name": ["in", names]}, fields=["name", "title", "project"]) if names else []

@frappe.whitelist()
def editor_options(project):
    doc = require_permission("Project", project)
    users = {r.user for r in doc.get("users") or []} | {doc.owner, frappe.session.user}
    return {"mentions": [{"id": user, "label": frappe.db.get_value("User", user, "full_name") or user, "value": user}
        for user in sorted(users) if user != "Guest" and frappe.has_permission("Project", "read", doc=doc, user=user)],
        "tasks": frappe.get_list("Task", filters={"project": project}, fields=["name", "subject"], limit_page_length=0)}


@frappe.whitelist()
def sync_page(name, sequence=0, state=None, content=None, initialize=False):
    """Retry an atomic HTTP sync if snapshot isolation rejects its row lock.

    Never roll back an enclosing application transaction: direct callers with
    pending writes retain the normal Frappe exception/rollback semantics.
    """
    import time
    can_retry = not frappe.db.transaction_writes
    for attempt in range(3):
        try:
            return _sync_page(name, sequence, state, content, initialize)
        except frappe.QueryDeadlockError:
            if not can_retry or attempt == 2:
                raise
            frappe.db.rollback()
            time.sleep(0.02 * (attempt + 1))


def _sync_page(name, sequence=0, state=None, content=None, initialize=False):
    """Exchange durable Yjs updates under a page row lock.

    A state can compact the log only when based on every accepted update.
    Concurrent states are unioned, never overwritten. HTML is a sanitized
    search/revision projection and is accepted only from a caught-up client.
    Readers receive states but cannot submit one. Transport retries are harmless
    because Yjs updates are idempotent; exact retries are deduplicated here too.
    """
    import base64
    import binascii
    from frappe.utils import cint
    require_permission("Pulse Document", name, "write" if state else "read")
    if state:
        if not isinstance(state, str) or len(state) > 4_000_000:
            frappe.throw("Page collaboration state is too large")
        try:
            decoded = base64.b64decode(state, validate=True)
            if not decoded:
                raise ValueError()
        except (ValueError, binascii.Error):
            frappe.throw("Invalid collaboration state")
    # Locking reads see the latest committed state even if the permission
    # lookup already established a transaction snapshot.
    doc = frappe.get_doc("Pulse Document", name, for_update=True)
    updates = frappe.parse_json(doc.get("collab_updates") or "[]")
    current = cint(doc.get("collab_sequence"))
    caught_up = cint(sequence) == current
    if state and not (cint(initialize) and updates):
        if caught_up:
            next_updates = [state]
        else:
            next_updates = updates if state in updates else [*updates, state]
        if sum(map(len, next_updates)) > 12_000_000:
            frappe.throw("Refresh this page to synchronize before continuing")
        if next_updates != updates:
            current += 1
            # Operational state is not a human revision and must not produce a
            # Version row on every keystroke. The content projection below does.
            frappe.db.set_value("Pulse Document", name, {
                "collab_updates": frappe.as_json(next_updates),
                "collab_sequence": current,
            }, update_modified=False)
            updates = next_updates
        if caught_up and content is not None and content != doc.content:
            doc.reload()
            doc.content = content
            doc.save(ignore_version=False)
    return {"states": updates, "sequence": current, "modified": str(doc.modified)}
