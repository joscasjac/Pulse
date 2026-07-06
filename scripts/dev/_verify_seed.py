import frappe

def run():
    counts = {
        "Pulse Objective": frappe.db.count("Pulse Objective"),
        "Pulse Key Result": frappe.db.count("Pulse Key Result"),
        "Pulse OKR Check-in": frappe.db.count("Pulse OKR Check-in"),
        "Pulse Risk": frappe.db.count("Pulse Risk"),
        "Pulse Retrospective": frappe.db.count("Pulse Retrospective"),
        "Pulse Meeting": frappe.db.count("Pulse Meeting"),
        "Pulse Decision": frappe.db.count("Pulse Decision"),
        "Pulse Allocation": frappe.db.count("Pulse Allocation"),
        "Pulse Leave": frappe.db.count("Pulse Leave"),
        "Pulse Portfolio": frappe.db.count("Pulse Portfolio"),
        "Pulse Health Check": frappe.db.count("Pulse Health Check"),
        "Pulse Change Request": frappe.db.count("Pulse Change Request"),
        "Pulse CR Approval": frappe.db.count("Pulse CR Approval"),
        "Pulse Dependency": frappe.db.count("Pulse Dependency"),
        "Pulse Timesheet": frappe.db.count("Pulse Timesheet"),
    }

    print("=== Seed Data Verification ===")
    total = 0
    for dt, count in sorted(counts.items()):
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {dt}: {count}")
        total += count
    print(f"\nTotal records created: {total}")
    
    if all(c > 0 for c in counts.values()):
        print("\n✓ All features have seed data!")
    else:
        missing = [dt for dt, c in counts.items() if c == 0]
        print(f"\n✗ Missing data for: {', '.join(missing)}")
