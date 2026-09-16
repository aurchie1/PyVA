"""
review_scheduling.py
Core auto-scheduling logic for compliance reviews:

1. schedule_initial_reviews(employee_id, hire_date)
   Called once, when a new employee is created. Creates one scheduled
   review per active review_type, due at hire_date + frequency.

2. generate_next_review(review_id)
   Called when a review is marked 'completed'. Looks up its review_type's
   frequency, computes the next due date from the completed_date, and
   inserts the follow-up scheduled review. Marks the original review's
   next_review_generated flag so this never double-creates.
"""

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from db import get_connection


def _add_frequency(start_date: date, frequency: int, frequency_unit: str) -> date:
    """Adds a frequency/unit pair (e.g. 6 months, 2 weeks) to a date."""
    if frequency_unit == "days":
        return start_date + relativedelta(days=frequency)
    elif frequency_unit == "weeks":
        return start_date + relativedelta(weeks=frequency)
    elif frequency_unit == "months":
        return start_date + relativedelta(months=frequency)
    else:
        raise ValueError(f"Unknown frequency_unit: {frequency_unit}")


def get_active_review_types():
    """Returns all review_types where is_active = 1."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT review_type_id, name, frequency, frequency_unit "
            "FROM review_types WHERE is_active = 1"
        ).fetchall()
    finally:
        conn.close()


def schedule_initial_reviews(employee_id: int, hire_date: str = None) -> list:
    """
    Creates one scheduled compliance_reviews row per active review_type
    for a newly created employee. The due date is hire_date + frequency
    for each type; if hire_date is missing, uses today as the baseline.

    Returns the list of newly created review_ids.
    """
    baseline = (
        datetime.strptime(hire_date, "%Y-%m-%d").date()
        if hire_date else date.today()
    )

    review_types = get_active_review_types()
    created_ids = []

    conn = get_connection()
    try:
        for rt in review_types:
            due_date = _add_frequency(baseline, rt["frequency"], rt["frequency_unit"])
            cursor = conn.execute(
                """
                INSERT INTO compliance_reviews
                    (employee_id, review_type_id, scheduled_date, status)
                VALUES (?, ?, ?, 'scheduled')
                """,
                (employee_id, rt["review_type_id"], due_date.isoformat()),
            )
            created_ids.append(cursor.lastrowid)
        conn.commit()
    finally:
        conn.close()

    return created_ids


def backfill_missing_reviews() -> dict:
    """
    Catches up any active employee who is missing a compliance_reviews
    row entirely for one or more active review types. This covers two
    situations:
      1. Employees added before auto-scheduling existed.
      2. A new review type was added after some employees already existed.

    For each (employee, review_type) pair with NO existing review row at
    all (scheduled, completed, waived - any status), creates one initial
    scheduled review using the employee's hire_date as the baseline (or
    today, if hire_date is missing).

    Employee/type pairs that already have at least one review row are
    left untouched, so running this multiple times is always safe and
    never creates duplicates.

    Returns a summary dict: {"created": int, "employees_affected": int}
    """
    conn = get_connection()
    try:
        employees = conn.execute(
            "SELECT employee_id, hire_date FROM employees "
            "WHERE is_deleted = 0 AND employment_status = 'active'"
        ).fetchall()

        review_types = conn.execute(
            "SELECT review_type_id, frequency, frequency_unit "
            "FROM review_types WHERE is_active = 1"
        ).fetchall()

        created_count = 0
        affected_employee_ids = set()

        for emp in employees:
            employee_id = emp["employee_id"]
            baseline = (
                datetime.strptime(emp["hire_date"], "%Y-%m-%d").date()
                if emp["hire_date"] else date.today()
            )

            for rt in review_types:
                existing = conn.execute(
                    """
                    SELECT 1 FROM compliance_reviews
                    WHERE employee_id = ? AND review_type_id = ?
                    LIMIT 1
                    """,
                    (employee_id, rt["review_type_id"]),
                ).fetchone()

                if existing is not None:
                    continue  # already has at least one review of this type

                due_date = _add_frequency(baseline, rt["frequency"], rt["frequency_unit"])
                conn.execute(
                    """
                    INSERT INTO compliance_reviews
                        (employee_id, review_type_id, scheduled_date, status)
                    VALUES (?, ?, ?, 'scheduled')
                    """,
                    (employee_id, rt["review_type_id"], due_date.isoformat()),
                )
                created_count += 1
                affected_employee_ids.add(employee_id)

        conn.commit()
    finally:
        conn.close()

    return {"created": created_count, "employees_affected": len(affected_employee_ids)}


def generate_next_review(review_id: int):
    """
    Given a review_id that was just marked 'completed', creates its
    follow-up scheduled review based on the review_type's frequency,
    and marks next_review_generated = 1 on the original so this is
    never run twice for the same review.

    Returns the new review_id, or None if the review type isn't found
    or the follow-up was already generated.
    """
    conn = get_connection()
    try:
        review = conn.execute(
            """
            SELECT cr.review_id, cr.employee_id, cr.review_type_id,
                   cr.completed_date, cr.next_review_generated,
                   rt.frequency, rt.frequency_unit
            FROM compliance_reviews cr
            JOIN review_types rt ON rt.review_type_id = cr.review_type_id
            WHERE cr.review_id = ?
            """,
            (review_id,),
        ).fetchone()

        if review is None or review["next_review_generated"]:
            return None

        completed = review["completed_date"] or date.today().isoformat()
        completed_date = datetime.strptime(completed, "%Y-%m-%d").date()
        next_due = _add_frequency(completed_date, review["frequency"], review["frequency_unit"])

        cursor = conn.execute(
            """
            INSERT INTO compliance_reviews
                (employee_id, review_type_id, scheduled_date, status)
            VALUES (?, ?, ?, 'scheduled')
            """,
            (review["employee_id"], review["review_type_id"], next_due.isoformat()),
        )
        new_review_id = cursor.lastrowid

        conn.execute(
            "UPDATE compliance_reviews SET next_review_generated = 1 WHERE review_id = ?",
            (review_id,),
        )
        conn.commit()
        return new_review_id
    finally:
        conn.close()