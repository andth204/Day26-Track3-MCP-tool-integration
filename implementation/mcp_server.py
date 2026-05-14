"""FastMCP server exposing a SQLite database via search / insert / aggregate."""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import DB_PATH, create_database

if not DB_PATH.exists():
    create_database()

adapter = SQLiteAdapter(DB_PATH)

mcp = FastMCP(
    name="sqlite-lab",
    instructions=(
        "Use this server when you need to read or write rows in the SQLite lab "
        "database (students, courses, enrollments). "
        "Always call schema://database first if you do not know the table layout."
    ),
)


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, **extra}


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


@mcp.tool(name="search")
def search(
    table: str,
    columns: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows from a table with optional filters, projection, ordering, and paging.

    Args:
        table: Target table name. Must be a known table.
        columns: Optional list of columns to return. Omit for all columns.
        filters: List of {"column": str, "op": str, "value": any}. Operators:
                 eq, ne, lt, lte, gt, gte, like, in.
        limit: Maximum rows (1 to 1000).
        offset: Rows to skip.
        order_by: Optional column to order by.
        descending: If true, order DESC; otherwise ASC.

    Returns:
        {"ok": true, "data": {rows, count, limit, offset, table}} on success,
        {"ok": false, "error": "..."} on validation failure.
    """
    try:
        return _ok(
            adapter.search(
                table=table,
                columns=columns,
                filters=filters,
                limit=limit,
                offset=offset,
                order_by=order_by,
                descending=descending,
            )
        )
    except ValidationError as e:
        return _error(str(e))
    except Exception as e:
        return _error(f"Internal error: {e}")


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert a single row into a table.

    Args:
        table: Target table name.
        values: Non-empty object whose keys are valid column names for the table.

    Returns:
        {"ok": true, "data": {inserted_id, row, table}} on success,
        {"ok": false, "error": "..."} on validation failure.
    """
    try:
        return _ok(adapter.insert(table=table, values=values))
    except ValidationError as e:
        return _error(str(e))
    except Exception as e:
        return _error(f"Internal error: {e}")


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Compute an aggregate over a table.

    Args:
        table: Target table name.
        metric: One of count, avg, sum, min, max.
        column: Required for all metrics except count.
        filters: Optional list of filter objects (same shape as search).
        group_by: Optional column to group by.

    Returns:
        {"ok": true, "data": {rows: [{value, ...}], metric, table, ...}}.
    """
    try:
        return _ok(
            adapter.aggregate(
                table=table,
                metric=metric,
                column=column,
                filters=filters,
                group_by=group_by,
            )
        )
    except ValidationError as e:
        return _error(str(e))
    except Exception as e:
        return _error(f"Internal error: {e}")


@mcp.resource("schema://database")
def database_schema() -> str:
    """Full database schema as JSON: table -> list of column descriptors."""
    return json.dumps(adapter.get_full_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Schema for a single table as JSON."""
    try:
        return json.dumps(
            {table_name: adapter.get_table_schema(table_name)},
            indent=2,
        )
    except ValidationError as e:
        return json.dumps({"error": str(e)}, indent=2)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
