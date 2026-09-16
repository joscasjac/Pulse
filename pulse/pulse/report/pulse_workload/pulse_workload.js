frappe.query_reports['Pulse Workload'] = {
  filters: [
    {fieldname: 'project', label: __('Project'), fieldtype: 'Link', options: 'Project'},
    {fieldname: 'start_date', label: __('From'), fieldtype: 'Date', default: frappe.datetime.get_today(), reqd: 1},
    {fieldname: 'end_date', label: __('To'), fieldtype: 'Date', default: frappe.datetime.add_days(frappe.datetime.get_today(), 13), reqd: 1},
  ],
};
