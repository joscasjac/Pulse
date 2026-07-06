import json, sys

path = "sites/project.local/site_config.json"
with open(path) as f:
    cfg = json.load(f)

if sys.argv[1] == "on":
    cfg["developer_mode"] = 1
    print("Developer mode ON")
elif sys.argv[1] == "off":
    cfg.pop("developer_mode", None)
    print("Developer mode OFF")

with open(path, "w") as f:
    json.dump(cfg, f, indent=1)
