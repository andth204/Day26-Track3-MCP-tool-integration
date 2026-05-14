# SQLite Lab MCP Server

FastMCP server exposing a small SQLite database (students / courses / enrollments)
through three tools and two resources.

Status: **13/13 tests passing**, end-to-end smoke test passes against an in-process
FastMCP client, MCP Inspector confirms tool + resource discovery, and the server
is verified working from Claude Code via `.mcp.json`.

## Project structure

```
implementation/
├── db.py                 SQLiteAdapter — validation + parameterized SQL.
├── init_db.py            Creates lab.db with seed data (idempotent).
├── mcp_server.py         FastMCP server with @tool and @resource handlers.
├── verify_server.py      In-process smoke test (no Inspector required).
├── tests/test_server.py  Pytest unit tests for the adapter.
├── start_inspector.ps1   Launches MCP Inspector pointing at this server.
├── .mcp.json             Claude Code project-level MCP config.
├── requirements.txt
├── screenshots/          Verification evidence (see "Verification" below).
└── lab.db                Generated SQLite file.
```

## Tools

| Name        | Purpose                                                                  |
| ----------- | ------------------------------------------------------------------------ |
| `search`    | Filter, project, order, and paginate rows from a table.                  |
| `insert`    | Insert one row into a table.                                             |
| `aggregate` | Compute `count` / `avg` / `sum` / `min` / `max`, with optional GROUP BY. |

Supported filter operators: `eq, ne, lt, lte, gt, gte, like, in`.
Supported metrics: `count, avg, sum, min, max`.

## Resources

| URI                            | Description                          |
| ------------------------------ | ------------------------------------ |
| `schema://database`            | Full schema for every table as JSON. |
| `schema://table/{table_name}`  | Schema for a single table as JSON.   |

## Safety

* All identifiers (table, column, order-by, group-by) are validated against the
  live SQLite catalog before any SQL is built.
* All user values go through parameterized placeholders (`?`).
* Tools never raise; they return `{"ok": false, "error": "..."}` on failure so
  the LLM can recover and the host can surface a clean error.

## Setup (Windows / PowerShell)

```powershell
cd implementation
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
```

`init_db.py` is safe to re-run while another process (e.g. a running MCP server)
still holds `lab.db` open — it relies on `DROP TABLE IF EXISTS` instead of
deleting the file.

## Verify

Run the in-process smoke test (no Inspector, no LLM needed):

```powershell
python verify_server.py
```

Expected: tool discovery, resource discovery, three valid tool calls, and four
invalid calls each return cleanly. Final line should read `ALL CHECKS PASSED`.

Run unit tests:

```powershell
pytest tests -v
```

Expected: **13 passed**.

## Test with MCP Inspector

```powershell
.\start_inspector.ps1
```

Open the URL printed in the terminal that contains `MCP_PROXY_AUTH_TOKEN=...`
(opening the plain `http://localhost:6274` will stay disconnected). In the
sidebar:

* **Command**: `.venv\Scripts\python.exe`
* **Arguments**: `mcp_server.py`
* Click **Connect** — the status pill turns green.

Then walk through:

1. **Tools** tab → **List Tools** → confirm `search`, `insert`, `aggregate`
   appear with input schemas.
2. **Resources** tab → **List Resources** → confirm `schema://database`.
3. **Resources** tab → **List Templates** → confirm `schema://table/{table_name}`.
4. Call `search` with `{"table": "students", "limit": 3}` → expect 3 rows and
   `ok: true`.
5. Call `search` with `{"table": "ghost"}` → expect `ok: false, error: "Unknown table: 'ghost'"`.
6. Call `aggregate` with `{"table":"students","metric":"avg","column":"score","group_by":"cohort"}` → expect one row per cohort.
7. Read `schema://database` → expect JSON for all three tables.

## Verification Evidence (screenshots)

| Screenshot                       | Shows                                                                  |
| -------------------------------- | ---------------------------------------------------------------------- |
| `screenshots/tools-list-1.jpg`   | Inspector connected; `search` tool selected with input schema visible. |
| `screenshots/tools-list-2.jpg`   | Inspector `insert` tool with schema + sample run.                      |
| `screenshots/tools-list-3.jpg`   | Inspector `aggregate` tool with schema + sample run.                   |
| `screenshots/resources.jpg`      | Inspector `schema://database` resource opened, JSON content visible.   |
| `screenshots/search-error.jpg`   | Inspector showing `ok: false, error: "Unknown table: 'ghost'"`.        |
| `screenshots/mcp_connected.jpg`  | Claude Code `/mcp` listing `sqlite-lab · ✓ connected · 3 tools`.       |
| `screenshots/agent_call_tool.jpg`| Claude Code calling `sqlite-lab.search` and rendering the result.      |

## Connect to a client

### Claude Code (verified)

A ready `.mcp.json` is committed in this directory. Open Claude Code with this
folder as the working directory and run:

```text
/mcp
```

The `sqlite-lab` server should appear as connected with 3 tools. Reference the
schema in chat with `@sqlite-lab:schema://database`.

The shipped `.mcp.json` uses absolute paths to the venv Python and this
directory. Adjust them after cloning to a different machine:

```jsonc
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "<abs path to .venv/Scripts/python.exe>",
      "args": ["mcp_server.py"],
      "cwd": "<abs path to implementation/>",
      "env": {}
    }
  }
}
```

### Gemini CLI

```powershell
gemini mcp add sqlite-lab `
  "$PWD\.venv\Scripts\python.exe" `
  "$PWD\mcp_server.py" `
  --description "SQLite lab FastMCP server" `
  --timeout 10000

gemini mcp list
gemini --allowed-mcp-server-names sqlite-lab --yolo `
  -p "Use the sqlite-lab server. Show the top 2 students by score."
```

### Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.sqlite_lab]
command = "ABSOLUTE/PATH/TO/.venv/Scripts/python.exe"
args    = ["ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
```

## Example tool calls

```jsonc
// search all students in cohort A1
{"table": "students", "filters": [{"column": "cohort", "op": "eq", "value": "A1"}]}

// top 3 students by score, descending
{"table": "students", "order_by": "score", "descending": true, "limit": 3}

// insert a student
{"table": "students", "values": {"name": "New Student", "cohort": "A1", "score": 7.5}}

// count enrollments
{"table": "enrollments", "metric": "count"}

// average score per cohort
{"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"}
```

## Troubleshooting

* **`PermissionError: ... lab.db`** — another process (Claude Code, Inspector)
  is holding the database. Either close that process, or just re-run
  `python init_db.py`: it now reuses the existing file and only drops/recreates
  tables, so it works even while the DB is open.
* **Inspector stuck on "Disconnected" / "Connection Error"** — open the URL
  that contains `MCP_PROXY_AUTH_TOKEN=...` (not the bare
  `http://localhost:6274`), and make sure **Command** and **Arguments** in the
  sidebar are populated correctly (`\.venv\Scripts\python.exe` and
  `mcp_server.py`). Paths containing spaces (e.g. `Track 3\Day 11`) get split
  when passed via CLI; type them into the UI fields directly instead.
* **`ModuleNotFoundError: fastmcp`** — the wrong Python is being used. Confirm
  the venv is activated (`.\.venv\Scripts\Activate.ps1`) or use the venv's
  python directly: `.\.venv\Scripts\python.exe mcp_server.py`.
* **Claude Code shows `sqlite-lab` failed** — run `claude --debug` to see the
  spawn error. Most commonly the `.mcp.json` paths point to the wrong machine.

## Bonus

To run over HTTP instead of stdio (for remote production scenarios):

```python
# at the bottom of mcp_server.py
mcp.run(transport="streamable-http", host="127.0.0.1", port=8765)
```
