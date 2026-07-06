import frappe


def extend_bootinfo(bootinfo):
    bootinfo.pulse_settings = (
        frappe.get_single("Pulse Settings")
        if frappe.db.exists("DocType", "Pulse Settings")
        else {}
    )
