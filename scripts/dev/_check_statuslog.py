import frappe

def run():
    cols = frappe.db.get_column_list("tabPulse Task Status Log")
    print("Pulse Task Status Log columns:")
    for c in cols:
        print(f"  {c}")
    
    data = frappe.get_all("Pulse Task Status Log", fields=["*"], limit=5)
    print("\nSample data:")
    for d in data:
        print(f"  {d}")
