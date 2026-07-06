import frappe, json

def run():
    out = {}
    dts = frappe.get_all("DocType", filters={"module": "Pulse"}, pluck="name")
    for dt in dts:
        meta = frappe.get_meta(dt)
        links, tables, selects = {}, {}, {}
        for f in meta.fields:
            if f.fieldtype == "Link":
                links[f.fieldname] = f.options
            elif f.fieldtype == "Table":
                tables[f.fieldname] = f.options
            elif f.fieldtype == "Select" and f.reqd:
                selects[f.fieldname] = (f.options or "").split("\n")[0]
        out[dt] = {"istable": meta.istable, "issingle": meta.issingle,
                   "links": links, "tables": tables, "reqd_selects": selects}
    print("===JSON===")
    print(json.dumps(out, indent=0))
