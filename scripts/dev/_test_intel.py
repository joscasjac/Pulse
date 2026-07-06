import frappe, json
from frappe.utils import nowdate, getdate

def run():
    # Check sprint field names
    sprint = frappe.get_all("Pulse Sprint", fields=["*"], limit=1)
    if sprint:
        print("Sprint keys:", list(sprint[0].keys()))
    
    # Check task field names
    task = frappe.get_all("Pulse Task", fields=["*"], limit=1)
    if task:
        print("Task keys:", [k for k in task[0].keys() if 'exp' in k.lower() or 'end' in k.lower() or 'sprint' in k.lower()])
    
    # Test the intelligence API
    from pulse.api import intelligence
    
    try:
        result = intelligence.get_intelligence_dashboard()
        print("\nIntelligence Dashboard:", json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nIntelligence error: {e}")
        import traceback
        traceback.print_exc()
