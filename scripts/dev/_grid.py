import frappe
frappe.set_user("Administrator")
frappe.local.form_dict = frappe._dict()
from frappe.desk.desktop import get_workspace_sidebar_items
res = get_workspace_sidebar_items()
pages = res.get("pages", [])
print("HAS_PULSE", any(p.get("name") == "Pulse" for p in pages))
print("PULSE_ROW", [p for p in pages if p.get("name") == "Pulse"])
print("APPS", sorted({str(p.get("app")) for p in pages}))
