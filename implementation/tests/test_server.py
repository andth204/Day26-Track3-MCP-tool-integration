"""Pytest tests for the SQLite adapter and the FastMCP tools."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import SQLiteAdapter, ValidationError  # noqa: E402
from init_db import create_database  # noqa: E402


@pytest.fixture()
def adapter(tmp_path):
    db = tmp_path / "test.db"
    create_database(db)
    return SQLiteAdapter(db)


def test_list_tables(adapter):
    assert set(adapter.list_tables()) == {"students", "courses", "enrollments"}


def test_get_table_schema(adapter):
    cols = {c["name"] for c in adapter.get_table_schema("students")}
    assert {"id", "name", "cohort", "score"}.issubset(cols)


def test_search_basic(adapter):
    res = adapter.search("students", limit=5)
    assert res["count"] >= 1
    assert all("name" in r for r in res["rows"])


def test_search_with_filter(adapter):
    res = adapter.search(
        "students",
        filters=[{"column": "cohort", "op": "eq", "value": "A1"}],
    )
    assert all(r["cohort"] == "A1" for r in res["rows"])


def test_search_unknown_table(adapter):
    with pytest.raises(ValidationError):
        adapter.search("ghost")


def test_search_bad_operator(adapter):
    with pytest.raises(ValidationError):
        adapter.search(
            "students",
            filters=[{"column": "score", "op": "regex", "value": ".*"}],
        )


def test_insert_and_search(adapter):
    res = adapter.insert(
        "students",
        {"name": "Zed", "cohort": "Z9", "score": 5.5},
    )
    assert res["inserted_id"] > 0
    assert res["row"]["name"] == "Zed"


def test_insert_empty(adapter):
    with pytest.raises(ValidationError):
        adapter.insert("students", {})


def test_insert_unknown_column(adapter):
    with pytest.raises(ValidationError):
        adapter.insert("students", {"name": "X", "ghost_col": 1})


def test_aggregate_count(adapter):
    res = adapter.aggregate("students", metric="count")
    assert res["rows"][0]["value"] >= 6


def test_aggregate_avg_group_by(adapter):
    res = adapter.aggregate(
        "students", metric="avg", column="score", group_by="cohort"
    )
    cohorts = {row["cohort"] for row in res["rows"]}
    assert "A1" in cohorts


def test_aggregate_bad_metric(adapter):
    with pytest.raises(ValidationError):
        adapter.aggregate("students", metric="median", column="score")


def test_aggregate_missing_column(adapter):
    with pytest.raises(ValidationError):
        adapter.aggregate("students", metric="avg")
