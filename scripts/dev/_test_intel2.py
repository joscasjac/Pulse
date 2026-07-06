import frappe, json, traceback

def run():
    from pulse.pulse.api import intelligence
    
    try:
        result = intelligence.get_intelligence_dashboard()
        print("Intelligence Dashboard:", json.dumps(result, indent=2))
    except Exception as e:
        print(f"Intelligence error: {e}")
        traceback.print_exc()
    
    try:
        sprints = frappe.get_all("Pulse Sprint", pluck="name", limit=1)
        if sprints:
            burndown = intelligence.get_burndown_data(sprints[0])
            print(f"\nBurndown ({sprints[0]}):", json.dumps(burndown[:3], indent=2), "...")
    except Exception as e:
        print(f"Burndown error: {e}")
    
    try:
        velocity = intelligence.get_velocity_trend(sprints=3)
        print(f"\nVelocity trend:", json.dumps(velocity, indent=2))
    except Exception as e:
        print(f"Velocity error: {e}")
