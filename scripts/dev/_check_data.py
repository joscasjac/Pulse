import frappe

def run():
    print("=== PROJECTS ===")
    for p in frappe.get_all("Pulse Project", pluck="name"):
        print(f"  {p}")
    
    print("\n=== SPRINTS ===")
    for s in frappe.get_all("Pulse Sprint", pluck="name"):
        print(f"  {s}")
    
    print("\n=== TASKS (first 10) ===")
    for t in frappe.get_all("Pulse Task", fields=["name", "subject", "status", "project", "pulse_sprint"], limit=10):
        print(f"  {t.name}: {t.subject} [{t.status}] project={t.project} sprint={t.sprint}")
    total = frappe.db.count("Pulse Task")
    print(f"\nTotal tasks: {total}")
    
    print("\n=== USERS ===")
    for u in frappe.get_all("User", fields=["name", "full_name"], filters={"enabled": 1}):
        print(f"  {u.name}: {u.full_name}")
