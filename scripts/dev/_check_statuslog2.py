import frappe

def run():
    sql = "DESCRIBE `tabPulse Task Status Log`"
    cols = frappe.db.sql(sql, as_dict=True)
    print("Pulse Task Status Log columns:")
    for c in cols:
        print(f"  {c['Field']:30s} {c['Type']:20s}")
    
    data = frappe.get_all("Pulse Task Status Log", fields=["*"], limit=3)
    print("\nSample data:")
    for d in data:
        print(f"  {d}")
