# Pulse MCP server

Control Pulse from Claude in plain language — *"Create a task 'Fix login' in Operations, high priority, assign to erin@pulse.demo and put it in this sprint"* — and Claude will do it through these tools.

The server talks to your running Pulse site over the REST API (token auth). It's standalone Python; no ERPNext.

## Tools exposed

**Read:** `list_projects`, `list_tasks`, `get_task`, `list_sprints`, `list_users`
**Write:** `create_task`, `update_task`, `move_task`, `assign_task`, `unassign_task`,
`add_comment`, `add_subtask`, `add_dependency`, `delete_task`, `create_sprint`, `create_project`

Assignment obeys Pulse's hierarchy rule — the connected account can only assign at or below its own role level.

---

## 1. Install

```bash
cd apps/pulse/mcp
python -m venv .venv
# Windows:  .venv\Scripts\activate     Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
```

Note the **full path** to the venv's Python (`.venv\Scripts\python.exe` on Windows, `.venv/bin/python` elsewhere) — you'll point Claude at it.

## 2. Generate an API key + secret (one time)

The safest way — the secret is shown once, in the browser:

1. Open Pulse/Frappe in your browser and log in.
2. Click your avatar (top-right) → **My Settings**.
3. Scroll to **API Access** → click **Generate Keys**.
4. Copy the **API Secret** (shown once) and the **API Key**.

> Use a dedicated user (e.g. a "Pulse Bot" user with the `Pulse Manager` role) if you want the AI's actions scoped and attributable, rather than Administrator.

## 3. Point the server at your site

Env vars the server reads:

| Var | Example | Notes |
|---|---|---|
| `PULSE_SITE_URL` | `http://172.23.107.104:8000` | Reachable URL of the site |
| `PULSE_SITE_HOST` | `project.local` | Host header if the site is served by name (WSL/multi-tenant) |
| `PULSE_API_KEY` | *(from step 2)* | |
| `PULSE_API_SECRET` | *(from step 2)* | |

## 4. Connect it to Claude

### Claude Desktop
Edit `claude_desktop_config.json` (Settings → Developer → Edit Config) and add:

```json
{
  "mcpServers": {
    "pulse": {
      "command": "C:\\path\\to\\apps\\pulse\\mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\apps\\pulse\\mcp\\pulse_mcp_server.py"],
      "env": {
        "PULSE_SITE_URL": "http://172.23.107.104:8000",
        "PULSE_SITE_HOST": "project.local",
        "PULSE_API_KEY": "your_key_here",
        "PULSE_API_SECRET": "your_secret_here"
      }
    }
  }
}
```
Restart Claude Desktop. You'll see a 🔌 with the Pulse tools.

### Claude Code
```bash
claude mcp add pulse \
  --env PULSE_SITE_URL=http://172.23.107.104:8000 \
  --env PULSE_SITE_HOST=project.local \
  --env PULSE_API_KEY=your_key_here \
  --env PULSE_API_SECRET=your_secret_here \
  -- /path/to/apps/pulse/mcp/.venv/bin/python /path/to/apps/pulse/mcp/pulse_mcp_server.py
```

## 5. Try it

Ask Claude things like:
- "List my Pulse projects."
- "Create a task in Operations: 'Prepare Q3 report', high priority, due next Friday, assign to bob@pulse.demo."
- "Move PLS5-3 to In Progress and comment 'started'."
- "Add a sub-task 'Draft outline' under PLS5-3."
- "Create a sprint 'Sprint 12' in Operations, active, this fortnight."

---

### Running the server from WSL instead of Windows
If Pulse runs in WSL and you'd rather run the server there, set `command` to `wsl` and pass the interpreter + script as args, or install the requirements inside WSL and use that Python path. Either works — the server only needs network access to `PULSE_SITE_URL`.

### Security
- The API secret grants the connected user's permissions. Keep the config file private.
- Scope the bot user's role to limit what the AI can change.
- All writes go through Pulse's normal permission + hierarchy checks server-side.
