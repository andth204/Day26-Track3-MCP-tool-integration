"""End-to-end smoke test for the FastMCP server.

Spawns the server over stdio (in-process), lists tools and resources,
calls each tool, and prints a pass/fail summary.

Run:  python verify_server.py
"""

from __future__ import annotations

import asyncio
import json

from fastmcp import Client

from mcp_server import mcp


async def main() -> int:
    failures = 0
    async with Client(mcp) as client:
        print("=" * 60)
        print("Tool discovery")
        print("=" * 60)
        tools = await client.list_tools()
        names = [t.name for t in tools]
        print("tools:", names)
        for required in ("search", "insert", "aggregate"):
            if required not in names:
                print(f"  MISSING tool: {required}")
                failures += 1

        print()
        print("=" * 60)
        print("Resource discovery")
        print("=" * 60)
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        uris = [str(r.uri) for r in resources] + [t.uriTemplate for t in templates]
        print("resources/templates:", uris)
        if not any("schema://database" in u for u in uris):
            print("  MISSING resource: schema://database")
            failures += 1
        if not any("schema://table" in u for u in uris):
            print("  MISSING resource template: schema://table/{table_name}")
            failures += 1

        print()
        print("=" * 60)
        print("Valid calls")
        print("=" * 60)

        r = await client.call_tool("search", {"table": "students", "limit": 3})
        print("search students limit=3 ->", r.data)
        if not r.data.get("ok"):
            failures += 1

        r = await client.call_tool(
            "insert",
            {"table": "students", "values": {"name": "Test User", "cohort": "Z9", "score": 5.5}},
        )
        print("insert student ->", r.data)
        if not r.data.get("ok"):
            failures += 1

        r = await client.call_tool(
            "aggregate",
            {"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"},
        )
        print("avg score by cohort ->", r.data)
        if not r.data.get("ok"):
            failures += 1

        r = await client.read_resource("schema://database")
        schema = json.loads(r[0].text)
        print("schema://database tables:", list(schema.keys()))
        if "students" not in schema:
            failures += 1

        r = await client.read_resource("schema://table/students")
        print("schema://table/students ->", r[0].text[:200], "...")

        print()
        print("=" * 60)
        print("Invalid calls (must fail cleanly)")
        print("=" * 60)

        r = await client.call_tool("search", {"table": "ghost_table"})
        print("unknown table ->", r.data)
        if r.data.get("ok"):
            failures += 1

        r = await client.call_tool(
            "search", {"table": "students", "filters": [{"column": "score", "op": "regex", "value": ".*"}]}
        )
        print("bad operator ->", r.data)
        if r.data.get("ok"):
            failures += 1

        r = await client.call_tool("insert", {"table": "students", "values": {}})
        print("empty insert ->", r.data)
        if r.data.get("ok"):
            failures += 1

        r = await client.call_tool("aggregate", {"table": "students", "metric": "median", "column": "score"})
        print("bad metric ->", r.data)
        if r.data.get("ok"):
            failures += 1

    print()
    print("=" * 60)
    if failures == 0:
        print("ALL CHECKS PASSED")
        return 0
    print(f"FAILURES: {failures}")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
