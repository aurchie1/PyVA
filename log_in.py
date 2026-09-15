
# -*- coding: utf-8 -*-

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from auth import hash_password, verify_password

DB_PATH = 'PyVA_db.db'

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

conn.execute("""

        CREATE TABLE IF NOT EXISTS users (

            user_id     INTEGER PRIMARY KEY AUTOINCREMENT,

   
            username        TEXT,
            email           TEXT NOT NULL,
            password_hash   TEXT NOT NULL,
    
            first_name      TEXT NOT NULL,
            last_name       TEXT NOT NULL,
            display_name    TEXT,
            phone_number    TEXT,
            VBMS_name       TEXT, NOT NULL,

            role            TEXT NOT NULL DEFALUT 'user'
                                CHECK (role IN ('admin', 'manager', 'user')),
            is_active       INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))
            
            )

    """)
conn.commit()
conn.close()

def get_connection():
    conn = sqlite3.connect(DB)
