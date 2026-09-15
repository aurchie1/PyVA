# -*- coding: utf-8 -*-
"""
auth_manager.py
Authentication functions specific to the managers table.
Uses hash_password/verify_password from auth.py (bcrypt).
"""

from db import get_connection
from auth import verify_password


def get_manager_by_username(username: str):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT * FROM managers
            WHERE username = ? AND is_deleted = 0
            """,
            (username,),
        ).fetchone()
    finally:
        conn.close()


def update_last_login(manager_id: int):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE managers SET last_login_at = datetime('now') WHERE manager_id = ?",
            (manager_id,),
        )
        conn.commit()
    finally:
        conn.close()


def authenticate(username: str, password: str):
    """
    Returns the manager row if credentials are valid and the account
    is active, otherwise returns None.
    """
    manager = get_manager_by_username(username)
    if manager is None:
        return None
    if not manager["is_active"]:
        return None
    if not verify_password(password, manager["password_hash"]):
        return None
    return manager
