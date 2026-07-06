import frappe

def run():
    pulse = frappe.get_all("DocType", filters={"module": "Pulse"}, pluck="name")
    for dt in sorted(pulse):
        print(dt)
