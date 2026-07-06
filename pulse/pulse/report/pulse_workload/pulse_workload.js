frappe.query_reports["Pulse Workload"] = {
    "filters": [
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Pulse Project",
            "reqd": 1
        },
        {
            "fieldname": "sprint",
            "label": __("Sprint"),
            "fieldtype": "Link",
            "options": "Pulse Sprint",
            "get_query": function() {
                let project = frappe.query_report.get_filter_value("project");
                return {
                    filters: { project: project }
                };
            }
        },
        {
            "fieldname": "include_done",
            "label": __("Include Done"),
            "fieldtype": "Check"
        }
    ]
};
