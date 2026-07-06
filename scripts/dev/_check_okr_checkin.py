import frappe

def run():
    exists = frappe.db.exists("DocType", "Pulse OKR Check-in")
    print(f"Exists in DB: {exists}")
