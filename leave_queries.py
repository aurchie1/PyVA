"""
leave_queries.py
Data access functions for leave_records: creating entries, viewing a
single employee's leave history (past + upcoming), and a team-wide
"who's out" view grouped by date.
"""

from datetime import datetime
from db import get_connection


def create_leave_record(
    employee_id: int,
    leave_type: str,
    start_datetime: str,
    end_datetime: str,
    status: str = "approved",
    notes: str = None,
    logged_by_manager_id: int = None,
) -> int:
    """
    Inserts a new leave record. Datetimes should be 'YYYY-MM-DD HH:MM'.
    Returns the new leave_id.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO leave_records
                (employee_id, leave_type, start_datetime, end_datetime,
                 status, notes, logged_by_manager_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (employee_id, leave_type, start_datetime, end_datetime,
             status, notes, logged_by_manager_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def calculate_hours(start_datetime: str, end_datetime: str) -> float:
    """Computes hours between two 'YYYY-MM-DD HH:MM' strings."""
    fmt = "%Y-%m-%d %H:%M"
    start = datetime.strptime(start_datetime, fmt)
    end = datetime.strptime(end_datetime, fmt)
    delta = end - start
    return round(delta.total_seconds() / 3600, 2)


def get_leave_for_employee(employee_id: int):
    """
    Returns all leave_records for one employee, most recent first.
    Caller can split into past/upcoming using today's date.
    """
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT leave_id, leave_type, start_datetime, end_datetime,
                   status, notes
            FROM leave_records
            WHERE employee_id = ?
            ORDER BY start_datetime DESC
            """,
            (employee_id,),
        ).fetchall()
    finally:
        conn.close()


def get_team_leave_grouped(manager_id: int, days_ahead: int = 30, days_back: int = 7):
    """
    Returns leave_records for the manager's whole team within a window
    (default: 7 days back through 30 days ahead), ordered by start date,
    so the caller can group them by date for a "who's out" view.
    Only includes 'approved' leave by default (skips denied/cancelled).
    """
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                lr.leave_id,
                lr.leave_type,
                lr.start_datetime,
                lr.end_datetime,
                lr.status,
                e.employee_id,
                e.first_name,
                e.last_name
            FROM leave_records lr
            JOIN employees e ON e.employee_id = lr.employee_id
            WHERE e.manager_id = ?
              AND e.is_deleted = 0
              AND lr.status = 'approved'
              AND date(lr.start_datetime) BETWEEN date('now', ? || ' days') AND date('now', ? || ' days')
            ORDER BY lr.start_datetime ASC
            """,
            (manager_id, -days_back, days_ahead),
        ).fetchall()
    finally:
        conn.close()


def update_leave_status(leave_id: int, status: str) -> None:
    """Updates just the status of a leave record (e.g. approve/deny/cancel)."""
    if status not in ("pending", "approved", "denied", "cancelled"):
        raise ValueError(f"Invalid status: {status}")

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE leave_records SET status = ? WHERE leave_id = ?",
            (status, leave_id),
        )
        conn.commit()
    finally:
        conn.close()
