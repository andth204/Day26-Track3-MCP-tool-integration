"""SQLite adapter with safe identifier validation and parameterized SQL."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).parent / "lab.db"

ALLOWED_OPERATORS = {"eq", "ne", "lt", "lte", "gt", "gte", "like", "in"}
ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}

_OPERATOR_SQL = {
    "eq": "=",
    "ne": "!=",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "like": "LIKE",
}


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    # --- connection ----------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # --- introspection -------------------------------------------------

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            ).fetchall()
        return [r["name"] for r in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        self._validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [
            {
                "name": r["name"],
                "type": r["type"],
                "notnull": bool(r["notnull"]),
                "default": r["dflt_value"],
                "primary_key": bool(r["pk"]),
            }
            for r in rows
        ]

    def get_full_schema(self) -> dict[str, list[dict[str, Any]]]:
        return {t: self.get_table_schema(t) for t in self.list_tables()}

    # --- validation helpers --------------------------------------------

    def _validate_table(self, table: str) -> None:
        if not isinstance(table, str) or not table:
            raise ValidationError("Table name must be a non-empty string.")
        if table not in self.list_tables():
            raise ValidationError(f"Unknown table: {table!r}")

    def _validate_columns(self, table: str, columns: Iterable[str]) -> list[str]:
        valid = {c["name"] for c in self.get_table_schema(table)}
        out: list[str] = []
        for c in columns:
            if c not in valid:
                raise ValidationError(
                    f"Unknown column {c!r} for table {table!r}. "
                    f"Allowed: {sorted(valid)}"
                )
            out.append(c)
        return out

    def _build_where(
        self,
        table: str,
        filters: list[dict[str, Any]] | None,
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        if not isinstance(filters, list):
            raise ValidationError("filters must be a list of {column, op, value}.")

        clauses: list[str] = []
        params: list[Any] = []
        valid_cols = {c["name"] for c in self.get_table_schema(table)}

        for f in filters:
            if not isinstance(f, dict):
                raise ValidationError("Each filter must be an object.")
            col = f.get("column")
            op = f.get("op")
            val = f.get("value")
            if col not in valid_cols:
                raise ValidationError(f"Unknown filter column: {col!r}")
            if op not in ALLOWED_OPERATORS:
                raise ValidationError(
                    f"Unsupported operator {op!r}. Allowed: {sorted(ALLOWED_OPERATORS)}"
                )
            if op == "in":
                if not isinstance(val, list) or not val:
                    raise ValidationError("Operator 'in' requires a non-empty list value.")
                placeholders = ",".join(["?"] * len(val))
                clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)
            else:
                clauses.append(f"{col} {_OPERATOR_SQL[op]} ?")
                params.append(val)

        return " WHERE " + " AND ".join(clauses), params

    # --- core tools ----------------------------------------------------

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self._validate_table(table)

        if columns:
            cols = self._validate_columns(table, columns)
            select_clause = ", ".join(cols)
        else:
            select_clause = "*"

        where_sql, params = self._build_where(table, filters)

        order_sql = ""
        if order_by is not None:
            self._validate_columns(table, [order_by])
            order_sql = f" ORDER BY {order_by} {'DESC' if descending else 'ASC'}"

        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValidationError("limit must be an integer between 1 and 1000.")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer.")

        sql = f"SELECT {select_clause} FROM {table}{where_sql}{order_sql} LIMIT ? OFFSET ?"
        params = [*params, limit, offset]

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "rows": [dict(r) for r in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_table(table)
        if not isinstance(values, dict) or not values:
            raise ValidationError("values must be a non-empty object.")
        cols = self._validate_columns(table, values.keys())

        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        with self.connect() as conn:
            cursor = conn.execute(sql, [values[c] for c in cols])
            conn.commit()
            new_id = cursor.lastrowid
            row = conn.execute(
                f"SELECT * FROM {table} WHERE rowid = ?", [new_id]
            ).fetchone()

        return {
            "table": table,
            "inserted_id": new_id,
            "row": dict(row) if row else None,
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self._validate_table(table)

        if metric not in ALLOWED_METRICS:
            raise ValidationError(
                f"Unsupported metric {metric!r}. Allowed: {sorted(ALLOWED_METRICS)}"
            )

        if metric == "count":
            target = column if column else "*"
            if column is not None:
                self._validate_columns(table, [column])
            metric_sql = f"COUNT({target})"
        else:
            if column is None:
                raise ValidationError(f"Metric {metric!r} requires a column.")
            self._validate_columns(table, [column])
            metric_sql = f"{metric.upper()}({column})"

        where_sql, params = self._build_where(table, filters)

        group_sql = ""
        select_extra = ""
        if group_by is not None:
            self._validate_columns(table, [group_by])
            group_sql = f" GROUP BY {group_by}"
            select_extra = f"{group_by}, "

        sql = f"SELECT {select_extra}{metric_sql} AS value FROM {table}{where_sql}{group_sql}"

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "metric": metric,
            "column": column,
            "group_by": group_by,
            "rows": [dict(r) for r in rows],
        }
