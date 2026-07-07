import frappe

REMOVE = [
    "Pulse Project", "Pulse Task", "Pulse Project User", "Pulse Issue Type",
    "Pulse Holiday List", "Pulse Holiday", "Pulse Team", "Pulse Team Member",
    "Pulse Favorite", "Pulse Health Check", "Pulse Label",
]
for dt in REMOVE:
    if frappe.db.exists("DocType", dt):
        try:
            frappe.delete_doc("DocType", dt, force=1, ignore_permissions=True)
            print("DELETED", dt)
        except Exception as e:
            print("SKIP", dt, "::", str(e)[:150])
frappe.db.commit()
print("DONE removal")
