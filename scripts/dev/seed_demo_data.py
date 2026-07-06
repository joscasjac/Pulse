import frappe
import json
from datetime import datetime, timedelta

def execute():
    frappe.flags.in_test = True
    
    # 1. Create a Project
    project_name = "Alpha Website Redesign"
    project_doc = frappe.db.get_value("Pulse Project", {"project_name": project_name}, "name")
    if not project_doc:
        doc = frappe.get_doc({
            "doctype": "Pulse Project",
            "project_name": project_name,
            "status": "Open",
            "priority": "High"
        }).insert(ignore_permissions=True)
        project_doc = doc.name
    
    # 2. Create a Sprint
    sprint_name = "Sprint 1 - Foundations"
    sprint_doc = frappe.db.get_value("Pulse Sprint", {"sprint_name": sprint_name}, "name")
    if not sprint_doc:
        doc = frappe.get_doc({
            "doctype": "Pulse Sprint",
            "sprint_name": sprint_name,
            "project": project_doc,
            "status": "Active",
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        }).insert(ignore_permissions=True)
        sprint_doc = doc.name
        
    # 3. Create Workflow States for Board
    for state in ["Backlog", "To Do", "In Progress", "In Review", "Done"]:
        if not frappe.db.exists("Workflow State", state):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state}).insert(ignore_permissions=True)

    # 4. Create demo tasks
    tasks = [
        {"subject": "Setup React Native CLI", "status": "Completed", "ws": "Done", "priority": "High", "pts": 3, "days": -1},
        {"subject": "Configure Tailwind CSS", "status": "Pending Review", "ws": "In Review", "priority": "Medium", "pts": 2, "days": 0},
        {"subject": "Build Login Screen", "status": "Working", "ws": "In Progress", "priority": "Urgent", "pts": 5, "days": 2},
        {"subject": "Integrate Auth API", "status": "Open", "ws": "To Do", "priority": "High", "pts": 8, "days": 5},
        {"subject": "Design System Typography", "status": "Open", "ws": "To Do", "priority": "Low", "pts": 1, "days": 7},
        {"subject": "Create Dashboard layout", "status": "Open", "ws": "Backlog", "priority": "Medium", "pts": 5, "days": 10},
    ]
    
    for t in tasks:
        if frappe.db.exists("Pulse Task", {"subject": t["subject"]}):
            continue
            
        doc = frappe.get_doc({
            "doctype": "Pulse Task",
            "subject": t["subject"],
            "project": project_doc,
            "pulse_sprint": sprint_doc,
            "status": t["status"],
            "workflow_state": t["ws"],
            "priority": t["priority"],
            "pulse_story_points": t["pts"],
            "exp_end_date": (datetime.now() + timedelta(days=t["days"])).strftime("%Y-%m-%d"),
            "task_type": "Task"
        })
        
        doc._assign = json.dumps(["Administrator", frappe.session.user])
        doc.insert(ignore_permissions=True)
        
    frappe.db.commit()
    print("Demo data seeded successfully!")
