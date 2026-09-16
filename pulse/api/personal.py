"""Permission-aware navigation, private inbox and task subscriptions."""
import hashlib
from urllib.parse import quote
import frappe
from frappe.utils import cint, now_datetime
from pulse.hooks.permissions import require_permission

TITLES = {"Task": "subject", "Project": "project_name", "Pulse Document": "title"}


def _user():
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to use Pulse", frappe.PermissionError)
    return frappe.session.user


def destination(doctype, name):
    routes = {"Task": "/board?task=", "Project": "/board?project=", "Pulse Document": "/documents?name="}
    return routes[doctype] + quote(str(name), safe="") if doctype in routes else None


def _visible(doctype, name, user=None):
    return doctype in TITLES and bool(name) and bool(frappe.db.exists(doctype, name)) and frappe.has_permission(doctype, "read", doc=name, user=user)


@frappe.whitelist()
def search(q=""):
    _user()
    q = str(q).strip()[:120]
    if len(q) < 2:
        return []
    results = []
    for doctype, title in TITLES.items():
        filters = [[title, "like", "%" + q + "%"]]
        if doctype == "Task":
            filters.append(["issue_key", "like", "%" + q + "%"])
        if doctype == "Pulse Document":
            filters.append(["content", "like", "%" + q + "%"])
        if not frappe.has_permission(doctype, "read"):
            continue
        for row in frappe.get_list(doctype, or_filters=filters, fields=["name", title], limit_page_length=20):
            if _visible(doctype, row.name):
                results.append({"doctype": doctype, "name": row.name, "title": row[title], "url": destination(doctype, row.name)})
    return results


def reference_query(table, user=None):
    """Constrain REST lists using native role, User Permission and row visibility."""
    user = user or frappe.session.user
    clauses = []
    for doctype in TITLES:
        if not frappe.has_permission(doctype, "read", user=user):
            continue
        names = frappe.get_list(doctype, pluck="name", limit_page_length=0, user=user)
        if names:
            allowed = ", ".join(frappe.db.escape(name) for name in names)
            clauses.append(f"(`tab{table}`.reference_doctype = {frappe.db.escape(doctype)} "
                           f"AND `tab{table}`.reference_name IN ({allowed}))")
    return "(" + " OR ".join(clauses) + ")" if clauses else "1=0"


def personal_query(user=None):
    return ("`tabPulse Personal Item`.`user` = " + frappe.db.escape(user or frappe.session.user)
            + " AND " + reference_query("Pulse Personal Item", user))


def personal_permission(doc, user=None, **kwargs):
    if doc.user != (user or frappe.session.user):
        return False
    if not _visible(doc.reference_doctype, doc.reference_name, user):
        return False
    return True


@frappe.whitelist()
def remember(doctype, name, kind="Recent", enabled=1):
    user = _user()
    if doctype not in TITLES or kind not in ("Recent", "Favorite", "Follow") or (kind == "Follow" and doctype != "Task"):
        frappe.throw("Unsupported personal item")
    require_permission(doctype, name)
    key = hashlib.sha256(f"{user}|{doctype}|{name}|{kind}".encode()).hexdigest()
    if not cint(enabled):
        if frappe.db.exists("Pulse Personal Item", key):
            frappe.delete_doc("Pulse Personal Item", key, ignore_permissions=True)
        return False
    if frappe.db.exists("Pulse Personal Item", key):
        frappe.db.set_value("Pulse Personal Item", key, "last_opened", now_datetime())
    else:
        frappe.get_doc({"doctype": "Pulse Personal Item", "name": key, "user": user,
                        "reference_doctype": doctype, "reference_name": name, "kind": kind,
                        "last_opened": now_datetime()}).insert(ignore_permissions=True)
    if kind == "Recent":
        stale = frappe.get_all("Pulse Personal Item", filters={"user": user, "kind": kind},
                               order_by="last_opened desc", limit_start=50, limit_page_length=0, pluck="name")
        for item in stale:
            frappe.delete_doc("Pulse Personal Item", item, ignore_permissions=True)
    return True


@frappe.whitelist()
def state(doctype, name):
    user = _user()
    if doctype not in TITLES:
        frappe.throw("Unsupported personal item")
    require_permission(doctype, name)
    return frappe.get_all("Pulse Personal Item", filters={"user": user,
        "reference_doctype": doctype, "reference_name": name}, pluck="kind")


@frappe.whitelist()
def items():
    user = _user()
    rows = frappe.get_all("Pulse Personal Item", filters={"user": user}, fields=["reference_doctype", "reference_name", "kind"], order_by="last_opened desc", limit_page_length=250)
    result = []
    for row in rows:
        if _visible(row.reference_doctype, row.reference_name):
            row.title = frappe.db.get_value(row.reference_doctype, row.reference_name, TITLES[row.reference_doctype])
            row.url = destination(row.reference_doctype, row.reference_name)
            result.append(row)
    return result


@frappe.whitelist()
def inbox(unread_only=0):
    user = _user()
    filters = {"recipient": user}
    if cint(unread_only):
        filters["is_read"] = 0
    rows = frappe.get_all("Pulse Notification", filters=filters, fields=["name", "message", "notification_type", "reference_doctype", "reference_name", "is_read", "creation"], order_by="creation desc", limit_page_length=200)
    result = []
    for row in rows:
        if _visible(row.reference_doctype, row.reference_name):
            row.url = destination(row.reference_doctype, row.reference_name)
            result.append(row)
    return result


@frappe.whitelist()
def mark_read(name, is_read=1):
    user = _user()
    doc = frappe.get_doc("Pulse Notification", name)
    if doc.recipient != user or not _visible(doc.reference_doctype, doc.reference_name):
        frappe.throw("Notification unavailable", frappe.PermissionError)
    frappe.db.set_value("Pulse Notification", name, {"is_read": 1 if cint(is_read) else 0, "is_seen": 1})
    frappe.publish_realtime("pulse_notification", {"refresh": True}, user=user, after_commit=True)


def notify(user, doctype, name, message, kind="System"):
    if frappe.flags.get("pulse_migration") or user == frappe.session.user or user == "Guest" or not _visible(doctype, name, user):
        return
    frappe.get_doc({"doctype": "Pulse Notification", "recipient": user,
                    "reference_doctype": doctype, "reference_name": name,
                    "notification_type": kind, "message": message,
                    "link_url": "/pulse" + destination(doctype, name)}).insert(ignore_permissions=True)
    frappe.publish_realtime("pulse_notification", {"refresh": True}, user=user, after_commit=True)


def _description_mentions(content):
    from bs4 import BeautifulSoup
    return {mention.get("data-id") for mention in BeautifulSoup(content or "", "html.parser").find_all(class_="mention")
            if mention.get("data-id") and mention.get("data-is-group") != "true"}


def task_updated(doc, method=None):
    if doc.flags.get("in_import") or frappe.flags.get("pulse_migration"):
        return
    before = doc.get_doc_before_save()
    old_description = before.get("description") if before else ""
    for user in _description_mentions(doc.get("description")) - _description_mentions(old_description):
        if frappe.db.exists("User", {"name": user, "enabled": 1}):
            notify(user, "Task", doc.name, f"{doc.subject}: you were mentioned in the description", "Mention")
    if not before:
        return
    changed = [field for field in ("subject", "status", "workflow_state", "priority", "exp_start_date", "exp_end_date", "description", "project") if doc.get(field) != before.get(field)]
    if not changed:
        return
    for user in frappe.get_all("Pulse Personal Item", filters={"kind": "Follow", "reference_doctype": "Task", "reference_name": doc.name}, pluck="user"):
        notify(user, "Task", doc.name, f"{doc.subject}: updated {', '.join(changed)}", "Status Change")


def assignment_created(doc, method=None):
    if doc.get("reference_type") == "Task" and doc.get("reference_name") and doc.get("allocated_to"):
        notify(doc.allocated_to, "Task", doc.reference_name, "A task was assigned to you", "Assignment")


def comment_created(doc, method=None):
    if not doc.get("task"):
        return
    for user in frappe.get_all("Pulse Personal Item", filters={"kind": "Follow", "reference_doctype": "Task", "reference_name": doc.task}, pluck="user"):
        notify(user, "Task", doc.task, "A new comment was added to a task you follow", "Comment")
