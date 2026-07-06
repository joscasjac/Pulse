import frappe

def execute():
    # Insert pulse-board if it doesn't exist, else reload it
    if not frappe.db.exists("Page", "pulse-board"):
        frappe.get_doc({
            "doctype": "Page",
            "page_name": "pulse-board",
            "module": "Pulse",
            "title": "Pulse Board",
            "standard": "Yes",
            "roles": [{"role": "System Manager"}, {"role": "Pulse Admin"}, {"role": "Pulse Manager"}]
        }).insert(ignore_permissions=True)
    frappe.reload_doc("pulse", "page", "pulse_board")
    print("pulse-board loaded!")

