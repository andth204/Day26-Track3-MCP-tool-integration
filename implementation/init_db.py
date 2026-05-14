"""Initialize the SQLite database used by the MCP server.

Run directly:  python init_db.py
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "lab.db"

SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    cohort   TEXT    NOT NULL,
    score    REAL    NOT NULL DEFAULT 0
);

CREATE TABLE courses (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    code   TEXT    NOT NULL UNIQUE,
    title  TEXT    NOT NULL,
    credits INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE enrollments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    course_id   INTEGER NOT NULL REFERENCES courses(id),
    grade       REAL
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, score) VALUES
    ('An Nguyen',  'A1', 8.5),
    ('Binh Tran',  'A1', 7.2),
    ('Chi Le',     'A2', 9.1),
    ('Dung Pham',  'A2', 6.8),
    ('Em Hoang',   'B1', 7.9),
    ('Phuc Vo',    'B1', 8.3);

INSERT INTO courses (code, title, credits) VALUES
    ('CS101', 'Intro to CS',           3),
    ('CS210', 'Data Structures',       4),
    ('AI301', 'Machine Learning',      3),
    ('DB220', 'Databases',             3);

INSERT INTO enrollments (student_id, course_id, grade) VALUES
    (1, 1, 8.0),
    (1, 2, 7.5),
    (2, 1, 6.5),
    (3, 3, 9.5),
    (3, 4, 8.8),
    (4, 2, 5.5),
    (5, 1, 7.0),
    (6, 3, 8.0);
"""


def create_database(db_path: Path = DB_PATH) -> Path:
    if db_path.exists():
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    path = create_database()
    print(f"Database created at: {path}")
