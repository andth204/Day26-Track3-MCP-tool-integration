# SQLite Lab MCP Server

FastMCP server exposing a small SQLite database (students / courses / enrollments)
through three tools and two resources.

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
  the LLM can recover.

## Setup

```powershell
cd implementation
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
```

## Verify

Run the in-process smoke test (no Inspector, no LLM needed):

```powershell
python verify_server.py
```

Run unit tests:

```powershell
pytest tests
```

## Test with MCP Inspector

```powershell
.\start_inspector.ps1
```

In the Inspector UI:

1. Open the **Tools** tab — confirm `search`, `insert`, `aggregate` appear with schemas.
2. Open the **Resources** tab — confirm `schema://database` and the
   `schema://table/{table_name}` template appear.
3. Call `search` with `{"table": "students", "limit": 3}` — expect 3 rows.
4. Call `search` with `{"table": "ghost"}` — expect a clean `ok: false` error.
5. Read `schema://database` — expect JSON for all three tables.
6. Read `schema://table/students` — expect JSON for the `students` table.

## Connect to a client

### Claude Code

Drop the `.mcp.json` file in your project root and replace `cwd` with the
absolute path to `implementation/`. Then in Claude Code:

```text
/mcp
```

The `sqlite-lab` server should appear as connected. Reference the schema with
`@sqlite-lab:schema://database`.

### Gemini CLI

```powershell
gemini mcp add sqlite-lab `
  (Get-Command python).Source `
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
command = "python"
args = ["ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
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

## Bonus

To run over HTTP instead of stdio:

```python
# at the bottom of mcp_server.py
mcp.run(transport="streamable-http", host="127.0.0.1", port=8765)
```
