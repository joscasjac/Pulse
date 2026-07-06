import frappe
doctypes = [
    "Pulse Objective", "Pulse Key Result", "Pulse OKR Check-in",
    "Pulse Risk", "Pulse Retrospective", "Pulse Meeting",
    "Pulse Decision", "Pulse Allocation", "Pulse Leave",
    "Pulse Portfolio", "Pulse Health Check", "Pulse Change Request",
    "Pulse Dependency", "Pulse Timesheet"
]
for d in doctypes:
    print(f"  {d}: {frappe.db.count(d)}")
