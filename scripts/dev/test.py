import frappe

def execute():
    tasks = frappe.get_all("Pulse Task", filters={"subject": "Setup React Native CLI"}, fields=["name", "subject", "status", "workflow_state", "_assign"])
    print("DEMO TASK:")
    for t in tasks:
        print(t)
