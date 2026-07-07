import traceback
from pulse.erpnext_bridge import migrate

try:
    r = migrate()
    print("RESULT projects", len(r["projects"]) if r else 0, "tasks", len(r["tasks"]) if r else 0)
except Exception as e:
    print("MIGERR", type(e).__name__, "::", str(e)[:400])
    traceback.print_exc()
