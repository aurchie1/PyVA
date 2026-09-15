"""
init_db.py
Creates (or updates) the SQLite database from schema.sql.

Usage:
    python init_db.py

Expects schema.sql to be in the same directory as this script.
Safe to re-run: all CREATE statements use IF NOT EXISTS, and the
seed data uses INSERT OR IGNORE, so re-running this won't duplicate
anything or wipe existing data.
"""

import sqlite3
import os

DB_PATH = 'PyVA_db.db'
SCHEMA_PATH = "schema.sql"


def init_db(db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH):
    if not os.path.exists(schema_path):
        raise FileNotFoundError(
            f"Could not find {schema_path}. Make sure it's in the same "
            f"directory as this script (current dir: {os.getcwd()})"
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)  # runs all statements in the file, including triggers
        conn.commit()
        print(f"Database ready at: {os.path.abspath(db_path)}")
    finally:
        conn.close()


def verify_tables(db_path: str = DB_PATH):
    """Quick sanity check: list all tables that now exist in the DB."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print("Tables in database:")
        for (name,) in rows:
            print(f"  - {name}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    verify_tables()
