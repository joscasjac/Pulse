import json
import os
import frappe
from frappe.modules.utils import sync_customizations
from frappe.core.doctype.doctype.doctype import make_meta

def run():
    json_path = frappe.get_app_path("pulse", "pulse", "doctype", "pulse_okr_check_in", "pulse_okr_check_in.json")
    print(f"JSON path: {json_path}")
    print(f"File exists: {os.path.exists(json_path)}")
    
    with open(json_path) as f:
        data = json.load(f)
    
    print(f"DocType name: {data.get('name')}")
    
    if frappe.db.exists("DocType", "Pulse OKR Check-in"):
        print("Already exists in DB - deleting and recreating")
        frappe.delete_doc("DocType", "Pulse OKR Check-in", force=1)
        frappe.db.commit()
    
    doc = frappe.get_doc(data)
    doc.db_insert()
    frappe.db.commit()
    print(f"Created DocType: {doc.name}")
