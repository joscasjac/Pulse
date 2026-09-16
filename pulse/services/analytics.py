"""Analytics calculated only from records already authorized for the viewer."""
import json
from collections import Counter

CLOSED = {"Completed", "Cancelled"}


def summarize(tasks, dependencies, sprints, today):
    by_name = {t["name"]: t for t in tasks}
    open_tasks = [t for t in tasks if t.get("status") not in CLOSED]
    blocked = {t["name"] for t in open_tasks if t.get("is_blocked", t.get("workflow_state") == "Blocked")}
    for dep in dependencies:
        source = by_name.get(dep.get("source_task"))
        target = by_name.get(dep.get("target_task"))
        if (dep.get("status") == "Active" and source and target
                and source.get("status") not in CLOSED and target.get("status") not in CLOSED):
            blocked.add(source["name"])
    done = sum(t.get("status") == "Completed" for t in tasks)
    workload = Counter()
    for task in open_tasks:
        try:
            assignees = json.loads(task.get("_assign") or "[]")
        except (ValueError, TypeError):
            assignees = []
        if isinstance(assignees, list):
            workload.update({u for u in assignees if isinstance(u, str)})

    def distribution(field):
        counts = Counter(t[field] for t in tasks if t.get(field))
        return [{"label": k, "value": v} for k, v in counts.most_common()]

    progress = []
    for sprint in sprints:
        members = [t for t in tasks if t.get("pulse_sprint") == sprint["name"]]
        completed = sum(t.get("status") == "Completed" for t in members)
        progress.append({"name": sprint.get("sprint_name") or sprint["name"],
                         "status": sprint.get("status"), "total": len(members), "done": completed,
                         "pct": round(100 * completed / len(members)) if members else 0})
    completion = {"estimated": len(tasks), "completed": done,
                  "pct": round(100 * done / len(tasks)) if tasks else 0}
    return {
        "kpis": {"completed": done, "blocked": len(blocked),
                 "flagged": sum(t.get("priority") in {"High", "Critical", "Urgent"} for t in open_tasks),
                 "delayed": sum(bool(t.get("exp_end_date")) and str(t["exp_end_date"])[:10] < str(today) for t in open_tasks)},
        "status_distribution": distribution("status"), "type_distribution": distribution("type"),
        "workload": [{"label": u, "value": n} for u, n in workload.most_common(8)],
        "completion": completion,
        # Compatibility for older clients: values remain explicitly task counts.
        "storypoints": completion,
        "sprint_progress": progress,
    }
