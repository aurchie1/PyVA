
import sqlite3

DB_PATH = 'PyVA_db.db'

conn = sqlite3.connect('PyVA_db.db')

cursor = conn.cursor()

cursor.execute("""

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
    is_active

    


)

""")
