# OpenCloudSkillHub — Platform Core (mcp-server)

The **platform core** of OpenCloudSkillHub: an MCP-first capability hub / agent school.
It is **skill-agnostic** — it serves knowledge (resources) and read-only tools, and never
executes anything on the user's machine (see `../docs/decisions/ADR-001`, `ADR-003`).

> Status: **Milestone 1** — a connectable FastMCP server exposing system resources and
> the generic catalog tools. No skill-specific tools. OCR course content lands later.

## What this server exposes (milestone 1)

**Resources (read-only):**
- `system://guide` — rules + map; the first thing an agent should read
- `school://curriculum` — how to learn any course
- `system://changelog` — version changes
- `skills://catalog` — index of courses (derived from skill manifests)

**Tools (generic, read-only):** `list_skills`, `search_skills`, `get_skill_detail`

## Requirements
- **Python 3.12** (pinned `>=3.12,<3.14`). Do **not** use 3.14 — OCR deps (milestone 4)
  lack 3.14 wheels. This machine has `py -3.12`.

## Setup (venv + pip)

```powershell
# from D:\Github\OpenCloudSkillHub\mcp-server
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

## Self-test (no MCP client needed)

```powershell
# from D:\Github\OpenCloudSkillHub
.\mcp-server\.venv\Scripts\python.exe scripts\selftest.py
```

Expected: prints the repo root, three readable system resources, `0 skill(s)` (skills/ is
empty in milestone 1), and `SELFTEST PASS`.

## Run the server (stdio)

```powershell
.\.venv\Scripts\python.exe -m opencloudskillhub.server
# or the console script:
.\.venv\Scripts\opencloudskillhub.exe
```

It speaks MCP over stdio and waits for a client; there is no human-facing output.

## Connect from Claude Code

Add to your MCP config (project `.mcp.json` or via `claude mcp add`). Use absolute paths.

```json
{
  "mcpServers": {
    "opencloudskillhub": {
      "command": "D:\\Github\\OpenCloudSkillHub\\mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "opencloudskillhub.server"],
      "env": { "OCSH_HOME": "D:\\Github\\OpenCloudSkillHub" }
    }
  }
}
```

`OCSH_HOME` is optional (the server auto-detects the repo root) but makes the content
location explicit and robust to where the client launches it.

Verify the connection by asking the agent to read `system://guide` and call `list_skills`.

## Layout

```
mcp-server/
  pyproject.toml
  src/opencloudskillhub/
    server.py     # FastMCP app: instructions + resources + tools
    registry.py   # scans ../skills/*/skill.yaml -> catalog (reads manifests as DATA)
    paths.py      # repo-root resolution + content reading
```

Content served by the server lives outside this dir: `../system/` (system resources)
and `../skills/` (courses). That separation is intentional — content is data, not code.
