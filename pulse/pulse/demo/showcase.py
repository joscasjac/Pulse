"""Pulse demo / showcase seeder.

Populates EVERY field of EVERY Pulse doctype with type-appropriate sample data so
the whole app can be reviewed visually. Standalone: touches only Pulse + framework
core doctypes (User/Role). Idempotent-ish: call clear() first to wipe prior demo data.

Run:
    bench --site <site> execute pulse.demo.showcase.run
    bench --site <site> execute pulse.demo.showcase.clear    # to remove demo data
"""

import random

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, nowtime, today

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Creation order = dependency order. Parents before children-that-link-to-them.
ORDER = [
    "Pulse Holiday List",
    "Pulse Project",
    "Pulse Team",
    "Pulse Sprint",
    "Pulse Task",
    "Pulse Label",
    "Pulse Checklist",
    "Pulse Comment",
    "Pulse Dependency",
    "Pulse Task Status Log",
    "Pulse Portfolio",
    "Pulse Objective",
    "Pulse Key Result",
    "Pulse OKR Check-in",
    "Pulse Goal",
    "Pulse Risk",
    "Pulse Meeting",
    "Pulse Decision",
    "Pulse Change Request",
    "Pulse CR Approval",
    "Pulse Retrospective",
    "Pulse Timesheet",
    "Pulse Allocation",
    "Pulse Leave",
    "Pulse Health Check",
    "Pulse Notification",
    "Pulse Activity Log",
    "Pulse Favorite",
    "Pulse Saved Filter",
]

HOW_MANY = 5          # default records per top-level doctype
CHILD_ROWS = 3        # rows per child table

# Doctypes that benefit from more volume for a richer visual demo.
COUNT_OVERRIDES = {
    "Pulse Task": 24,
    "Pulse Project": 5,
    "Pulse Sprint": 4,
    "Pulse Objective": 6,
    "Pulse Risk": 6,
    "Pulse Meeting": 6,
}

DEMO_USERS = [
    ("alice@pulse.demo", "Alice", "Nguyen", "Pulse Admin"),
    ("bob@pulse.demo", "Bob", "Martinez", "Pulse Manager"),
    ("carol@pulse.demo", "Carol", "Okafor", "Pulse Team Lead"),
    ("dan@pulse.demo", "Dan", "Petrov", "Pulse Senior Developer"),
    ("erin@pulse.demo", "Erin", "Cohen", "Pulse Junior Developer"),
    ("frank@pulse.demo", "Frank", "Li", "Pulse Intern"),
]

LOREM = (
    "This is representative sample content generated for the Pulse demo. It covers "
    "typical wording so every text field renders with something readable."
)
SENTENCES = [
    "Kick off the initiative and align the team on scope.",
    "Investigate the reported regression and add a failing test.",
    "Refactor the data layer for clarity and performance.",
    "Ship the customer-facing dashboard behind a feature flag.",
    "Document the API and publish the migration guide.",
    "Reduce flaky tests and stabilise the CI pipeline.",
]

created = {}  # doctype -> [names]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _users():
    return [u[0] for u in DEMO_USERS]


def _pick(doctype):
    names = created.get(doctype)
    if names:
        return random.choice(names)
    # fall back to any existing record in the DB
    existing = frappe.get_all(doctype, pluck="name", limit=1)
    return existing[0] if existing else None


def _sample_data(fieldname, label, idx):
    fn = (fieldname or "").lower()
    if "email" in fn:
        return f"contact{idx}@pulse.demo"
    if "url" in fn or "link" in fn:
        return "https://example.com/pulse"
    if "color" in fn:
        return random.choice(["#3b82f6", "#22c55e", "#ef4444", "#f97316", "#8b5cf6"])
    if "key" in fn:
        return f"PLS{idx}"
    if any(t in fn for t in ("name", "title", "subject", "summary")):
        return f"{label} {idx}"
    return f"{label} sample {idx}"


def _fill(doctype, idx, overrides=None, is_child=False):
    """Build a dict populating every field of `doctype`."""
    meta = frappe.get_meta(doctype)
    overrides = overrides or {}
    doc = {"doctype": doctype}
    # remember which field holds the doctype for each Dynamic Link
    for f in meta.fields:
        fn = f.fieldname
        ft = f.fieldtype
        if fn in overrides:
            if overrides[fn] is not None:
                doc[fn] = overrides[fn]
            continue
        if ft in ("Section Break", "Column Break", "Tab Break", "HTML", "Button",
                  "Image", "Fold", "Heading"):
            continue
        if ft in ("Attach", "Attach Image", "Signature", "Geolocation", "Barcode"):
            continue
        if ft == "Link":
            target = f.options
            if target == "User":
                doc[fn] = random.choice(_users())
            elif target == "Role":
                doc[fn] = random.choice([u[3] for u in DEMO_USERS])
            elif target == "DocType":
                doc[fn] = "Pulse Task"
            elif target == "Workflow State":
                doc[fn] = None
            elif target and target.startswith("Pulse"):
                doc[fn] = _pick(target)
            else:
                doc[fn] = None
        elif ft == "Dynamic Link":
            # options points to the fieldname holding the doctype
            ref_dt = doc.get(f.options) or "Pulse Task"
            doc[fn] = _pick(ref_dt)
        elif ft == "Table":
            doc[fn] = [
                _fill(f.options, i + 1, is_child=True)
                for i in range(CHILD_ROWS)
            ]
        elif ft in ("Data",):
            doc[fn] = _sample_data(fn, f.label or fn, idx)
        elif ft in ("Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor",
                    "Code", "HTML Editor"):
            doc[fn] = random.choice(SENTENCES) if "Text" != ft else LOREM
        elif ft == "Select":
            opts = [o for o in (f.options or "").split("\n") if o != ""]
            doc[fn] = random.choice(opts) if opts else None
        elif ft in ("Int",):
            doc[fn] = random.randint(1, 13)
        elif ft in ("Float", "Currency"):
            doc[fn] = round(random.uniform(1, 100), 2)
        elif ft == "Percent":
            doc[fn] = random.choice([10, 25, 40, 60, 75, 90])
        elif ft == "Check":
            doc[fn] = random.choice([0, 1])
        elif ft == "Date":
            doc[fn] = add_days(today(), random.randint(-20, 20))
        elif ft == "Datetime":
            doc[fn] = add_to_date(now_datetime(), hours=random.randint(-100, 100))
        elif ft == "Time":
            doc[fn] = nowtime()
        elif ft == "Duration":
            doc[fn] = random.choice([1800, 3600, 7200])
        elif ft == "Rating":
            doc[fn] = random.choice([0.4, 0.6, 0.8, 1.0])
        # else: leave unset
    return doc


def _insert(doctype, idx, overrides=None):
    data = _fill(doctype, idx, overrides=overrides)
    meta = frappe.get_meta(doctype)
    if (meta.autoname or "").lower() == "prompt":
        data["__newname"] = f"{doctype}-{idx}-{random.randint(1000, 9999)}"
    try:
        doc = frappe.get_doc(data)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()  # persist each record so a later failure can't roll it back
        created.setdefault(doctype, []).append(doc.name)
        return doc
    except Exception as e:
        frappe.db.rollback()  # only discards this failed partial insert (back to last commit)
        print(f"  ! {doctype} #{idx} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def ensure_users():
    for email, first, last, role in DEMO_USERS:
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": first,
                "last_name": last,
                "send_welcome_email": 0,
                "user_type": "System User",
            })
            u.flags.ignore_permissions = True
            u.insert(ignore_permissions=True)
        else:
            u = frappe.get_doc("User", email)
        for r in {role, "Pulse Viewer"}:
            if frappe.db.exists("Role", r) and r not in [d.role for d in u.roles]:
                u.append("roles", {"role": r})
        u.flags.ignore_permissions = True
        u.save(ignore_permissions=True)
    frappe.db.commit()  # persist users before seeding records that link to them
    print(f"  users ready: {', '.join(_users())}")


# ---------------------------------------------------------------------------
# Per-doctype overrides (relationship wiring the generic filler can't infer well)
# ---------------------------------------------------------------------------

def _overrides(doctype, idx):
    o = {}
    if doctype == "Pulse Sprint":
        start = add_days(today(), (idx - 2) * 14)
        o["start_date"] = start
        o["end_date"] = add_days(start, 13)
        o["status"] = ["Completed", "Completed", "Active", "Planned"][idx - 1]
    elif doctype == "Pulse Task":
        proj = _pick("Pulse Project")
        o["project"] = proj
        o["pulse_sprint"] = _pick("Pulse Sprint")
        # epic points to an earlier task (or none)
        o["pulse_epic"] = random.choice(created.get("Pulse Task", []) or [None])
        o["workflow_state"] = None
    elif doctype == "Pulse Dependency":
        tasks = created.get("Pulse Task", [])
        if len(tasks) >= 2:
            s, t = random.sample(tasks, 2)
            o["source_task"], o["target_task"] = s, t
            o["source_project"] = frappe.db.get_value("Pulse Task", s, "project")
            o["target_project"] = frappe.db.get_value("Pulse Task", t, "project")
    elif doctype == "Pulse Decision":
        o["superseded_by"] = None
    elif doctype == "Pulse Document":
        o["parent_doc"] = None
    return o


# ---------------------------------------------------------------------------
# Assignment (so boards / My Work show cards)
# ---------------------------------------------------------------------------

def assign_tasks():
    from frappe.desk.form.assign_to import add as assign_add
    users = _users()
    for i, name in enumerate(created.get("Pulse Task", [])):
        try:
            assign_add({
                "assign_to": [users[i % len(users)]],
                "doctype": "Pulse Task",
                "name": name,
            })
        except Exception as e:
            print(f"  ! assign {name} failed: {e}")


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def run():
    random.seed(7)
    print("Seeding Pulse demo data ...")
    ensure_users()
    for doctype in ORDER:
        n = COUNT_OVERRIDES.get(doctype, HOW_MANY)
        for i in range(1, n + 1):
            _insert(doctype, i, overrides=_overrides(doctype, i))
        print(f"  {doctype}: {len(created.get(doctype, []))}")
    assign_tasks()
    frappe.db.commit()
    total = sum(len(v) for v in created.values())
    print(f"Done. Created {total} top-level records across {len(created)} doctypes.")


def clear():
    """Remove demo data (child tables cascade with their parents)."""
    print("Clearing Pulse demo data ...")
    for doctype in reversed(ORDER):
        meta = frappe.get_meta(doctype)
        if meta.istable or meta.issingle:
            continue
        for name in frappe.get_all(doctype, pluck="name"):
            try:
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
            except Exception as e:
                print(f"  ! delete {doctype} {name}: {e}")
    for email in _users():
        if frappe.db.exists("User", email):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:
                pass
    frappe.db.commit()
    print("Cleared.")
