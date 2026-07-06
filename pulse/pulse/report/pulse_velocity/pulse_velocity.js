frappe.query_reports["Pulse Velocity"] = {
    "filters": [
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Pulse Project",
            "reqd": 1
        },
        {
            "fieldname": "last_n_sprints",
            "label": __("Last N Sprints"),
            "fieldtype": "Int",
            "default": 6
        }
    ]
};
