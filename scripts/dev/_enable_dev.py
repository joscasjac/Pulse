import frappe, os, json

def run():
    site = frappe.local.site
    config_path = frappe.get_site_path("site_config.json")
    
    with open(config_path) as f:
        config = json.load(f)
    
    config["developer_mode"] = 1
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=1)
    
    print(f"Developer mode enabled for {site}")
    print("Run migration now, then re-run this to disable")
