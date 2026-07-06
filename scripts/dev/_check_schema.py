import frappe

def run():
    cols = frappe.db.get_column_list("tabPulse Task")
    print("Pulse Task columns:")
    for c in cols:
        print(f"  {c}")
    
    print("\nPulse Sprint columns:")
    cols = frappe.db.get_column_list("tabPulse Sprint")
    for c in cols:
        print(f"  {c}")
