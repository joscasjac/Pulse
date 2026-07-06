import json, os, frappe

def run():
    json_path = frappe.get_app_path("pulse", "pulse", "doctype", "pulse_okr_check_in", "pulse_okr_check_in.json")
    with open(json_path) as f:
        data = json.load(f)
    
    name = data["name"]
    if frappe.db.exists("DocType", name):
        frappe.delete_doc("DocType", name, force=1, ignore_permissions=True)
        frappe.db.commit()
    
    doc = frappe.get_doc(data)
    doc.flags.ignore_permissions = True
    doc.insert()
    frappe.db.commit()
    print(f"Created: {doc.name}")
