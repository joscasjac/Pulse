"""Metadata for hosting tools that discover apps by the standard hooks.py path.

Python imports the sibling hooks package, whose __init__.py contains the runtime
registry. Keep these discovery fields in sync with that package.
"""
app_name = "pulse"
app_title = "Pulse"
app_publisher = "Frappe"
app_description = "Modern agile delivery layer on top of ERPNext Projects"
app_email = "info@frappe.io"
app_version = "0.2.0"
required_apps = ["erpnext"]
