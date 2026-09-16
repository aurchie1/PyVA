"""
compliance_queries.py
Data access for compliance_reviews: listing overdue/upcoming/all reviews
for a manager's team, and marking a review completed (which triggers
auto-scheduling of the follow-up via review_scheduling.py).
"""

from datetime import date
from db import get_connection
from review_scheduling import generate_next_review


def get_overdue_reviews(manager_id: int):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT cr.review_id, e.employee_id, e.first_name, e.last_name,
                   rt.name AS review_type_name, cr.scheduled_date
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


def get_upcoming_reviews(manager_id: int, days_ahead: int = 30):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT cr.review_id, e.employee_id, e.first_name, e.last_name,
                   rt.name AS review_type_name, cr.scheduled_date
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


def get_reviews_for_employee(employee_id: int):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT cr.review_id, rt.name AS review_type_name,
                   cr.scheduled_date, cr.completed_date, cr.status, cr.summary
            FROM compliance_reviews cr
            JOIN review_types rt ON rt.review_type_id = cr.review_type_id
            WHERE cr.employee_id = ?
            ORDER BY cr.scheduled_date DESC
            """,
            (employee_id,),
        ).fetchall()
    finally:
        conn.close()


def get_all_review_types():
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT review_type_id, name, frequency, frequency_unit, is_active "
            "FROM review_types ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def complete_review(review_id: int, conducted_by_manager_id: int, summary: str = None):
    """
    Marks a review completed (today's date), then triggers auto-scheduling
    of the follow-up review based on the review_type's frequency.

    Returns the new review_id for the auto-generated follow-up.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE compliance_reviews
            SET status = 'completed',
                completed_date = date('now'),
                conducted_by_manager_id = ?,
                summary = ?
            WHERE review_id = ?
            """,
            (conducted_by_manager_id, summary, review_id),
        )
        conn.commit()
    finally:
        conn.close()

    return generate_next_review(review_id)


def waive_review(review_id: int, summary: str = None):
    """Marks a review as waived (skipped) without generating a follow-up."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE compliance_reviews SET status = 'waived', summary = ? WHERE review_id = ?",
            (summary, review_id),
        )
        conn.commit()
    finally:
        conn.close()
