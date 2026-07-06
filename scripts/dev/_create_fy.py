import frappe

def run():
    fys = frappe.get_all("Fiscal Year", pluck="name")
    print(f"Existing Fiscal Years: {fys}")
    
    if "2026" not in fys:
        fy = frappe.get_doc({
            "doctype": "Fiscal Year",
            "year": "2026",
            "year_start_date": "2026-01-01",
            "year_end_date": "2026-12-31",
        })
        fy.flags.ignore_permissions = True
        fy.insert()
        print("Created Fiscal Year 2026")
    
    if "2025" not in fys:
        fy = frappe.get_doc({
            "doctype": "Fiscal Year",
            "year": "2025",
            "year_start_date": "2025-01-01",
            "year_end_date": "2025-12-31",
        })
        fy.flags.ignore_permissions = True
        fy.insert()
        print("Created Fiscal Year 2025")
