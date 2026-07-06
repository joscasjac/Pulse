import frappe

def execute():
    try:
        tasks = frappe.get_list(
            doctype='Pulse Task',
            fields=[
                'name', 'subject', 'project', 'status', 'workflow_state',
                'priority', 'task_type', 'pulse_story_points', 'pulse_sprint',
                'exp_start_date', 'exp_end_date', '_assign', 'owner',
                'pulse_rank', 'is_milestone', 'creation', 'modified'
            ],
            filters={'status': ['not in', ['Cancelled']]},
            limit_page_length=500,
            order_by='pulse_rank asc, creation asc'
        )
        print("SUCCESS:", len(tasks), "tasks fetched")
    except Exception as e:
        print("ERROR:", str(e))
