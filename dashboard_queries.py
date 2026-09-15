# -*- coding: utf-8 -*-
"""
dashboard_queries.py
Queries that power the dashboard: overdue compliance reviews and
employees who haven't hit the 2x/year recognition minimum.

All queries are scoped to a manager_id, so each manager only sees
their own team.
"""

from db import get_connection


def get_overdue_reviews(manager_id: int):
    """
    Returns compliance_reviews rows that are still 'scheduled' but past
    their scheduled_date, for employees under the given manager.
    """
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                cr.review_id,
                e.employee_id,
                e.first_name,
                e.last_name,
                rt.name AS review_type_name,
                cr.scheduled_date
            FROM compliance_reviews cr
            JOIN employees e ON e.employee_id = cr.employee_id
            JOIN review_types rt ON rt.review_type_id = cr.review_type_id
            WHERE cr.status = 'scheduled'
              AND cr.scheduled_date < date('now')
              AND e.manager_id = ?
              AND e.is_deleted = 0
            ORDER BY cr.scheduled_date ASC
            """,
            (manager_id,),
        ).fetchall()
    finally:
        conn.close()


def get_upcoming_reviews(manager_id: int, days_ahead: int = 14):
    """
    Returns compliance_reviews scheduled within the next N days
    (not yet overdue), useful for a 'coming up' section.
    """
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                cr.review_id,
                e.employee_id,
                e.first_name,
                e.last_name,
                rt.name AS review_type_name,
                cr.scheduled_date
            FROM compliance_reviews cr
            JOIN employees e ON e.employee_id = cr.employee_id
            JOIN review_types rt ON rt.review_type_id = cr.review_type_id
            WHERE cr.status = 'scheduled'
              AND cr.scheduled_date BETWEEN date('now') AND date('now', ? || ' days')
              AND e.manager_id = ?
              AND e.is_deleted = 0
            ORDER BY cr.scheduled_date ASC
            """,
            (days_ahead, manager_id),
        ).fetchall()
    finally:
        conn.close()


def get_recognition_gaps(manager_id: int, year: int):
    """
    Returns employees under this manager who have fewer than 2
    fulfilled recognition_schedule slots for the given year.
    Includes a count so the dashboard can show e.g. "1 of 2".
    """
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                e.employee_id,
                e.first_name,
                e.last_name,
                COUNT(CASE WHEN rs.status = 'fulfilled' THEN 1 END) AS fulfilled_count
            FROM employees e
            LEFT JOIN recognition_schedule rs
                ON rs.employee_id = e.employee_id AND rs.year = ?
            WHERE e.manager_id = ?
              AND e.is_deleted = 0
              AND e.employment_status = 'active'
            GROUP BY e.employee_id
            HAVING fulfilled_count < 2
            ORDER BY fulfilled_count ASC, e.last_name ASC
            """,
            (year, manager_id),
        ).fetchall()
    finally:
        conn.close()


def get_upcoming_wgi_dates(manager_id: int, days_ahead: int = 60):
    """
    Returns employees whose next within-grade increase date falls
    within the next N days.
    """
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT employee_id, first_name, last_name, next_wgi_date
            FROM employees
            WHERE manager_id = ?
              AND is_deleted = 0
              AND next_wgi_date IS NOT NULL
              AND next_wgi_date BETWEEN date('now') AND date('now', ? || ' days')
            ORDER BY next_wgi_date ASC
            """,
            (manager_id, days_ahead),
        ).fetchall()
    finally:
        conn.close()


def get_team_summary(manager_id: int):
    """Quick counts for dashboard tiles."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS active_count
            FROM employees
            WHERE manager_id = ? AND is_deleted = 0 AND employment_status = 'active'
            """,
            (manager_id,),
        ).fetchone()
        return {"active_employees": row["active_count"]}
    finally:
        conn.close()
