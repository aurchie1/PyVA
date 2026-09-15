# -*- coding: utf-8 -*-
"""
db.py
Central place for opening connections to PyVA_db.db.
Import get_connection() anywhere you need to talk to the database.
"""

import sqlite3

DB_PATH = "PyVA_db.db"


def get_connection() -> sqlite3.Connection:
    """
    Returns a new SQLite connection with foreign keys enabled and
    row_factory set so query results can be accessed by column name
    (e.g. row["first_name"]) instead of by index.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn
