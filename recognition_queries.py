"""
recognition_queries.py
Data access for recognition_log (actual thank-you notes/awards given)
and recognition_schedule (quarterly slots tracking the 2x/year goal).

Key behavior: logging a recognition entry auto-matches it to the
employee's current open quarter slot, or the next pending slot this
year if the current one is already fulfilled. If all four quarters
are already fulfilled, the entry is logged with no slot match.
"""

from datetime import date
from db import get_connection

QUARTER_MONTHS = {
    "Q1": (1, 3),
    "Q2": (4, 6),
    "Q3": (7, 9),
    "Q4": (10, 12),
}


def _quarter_window(year: int, period: str):
    """Returns (start_date, end_date) ISO strings for a given year/quarter."""
    start_month, end_month = QUARTER_MONTHS[period]
    start = date(year, start_month, 1)
    if end_month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, end_month + 1, 1) - __import__("datetime").timedelta(days=1)
    return start.isoformat(), end.isoformat()


def current_quarter(today: date = None) -> str:
    """Returns 'Q1'..'Q4' for the given date (defaults to today)."""
    today = today or date.today()
    month = today.month
    if month <= 3:
        return "Q1"
    elif month <= 6:
        return "Q2"
    elif month <= 9:
        return "Q3"
    else:
        return "Q4"


# =========================================================
# Schedule generation (the "backfill" equivalent for recognition)
# =========================================================
def generate_quarterly_slots(year: int) -> dict:
    """
    Creates the 4 quarterly recognition_schedule slots for every active
    employee for the given year, skipping any employee/year/period
    combination that already exists (safe to run multiple times).

    Returns {"created": int, "employees_affected": int}.
    """
    conn = get_connection()
    try:
        employees = conn.execute(
            "SELECT employee_id FROM employees WHERE is_deleted = 0 AND employment_status = 'active'"
        ).fetchall()

        created_count = 0
        affected_employee_ids = set()

        for emp in employees:
            employee_id = emp["employee_id"]
            for period in ("Q1", "Q2", "Q3", "Q4"):
                existing = conn.execute(
                    """
                    SELECT 1 FROM recognition_schedule
                    WHERE employee_id = ? AND year = ? AND period = ?
                    """,
                    (employee_id, year, period),
                ).fetchone()

                if existing is not None:
                    continue

                window_start, window_end = _quarter_window(year, period)
                conn.execute(
                    """
                    INSERT INTO recognition_schedule
                        (employee_id, year, period, window_start_date, window_end_date, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                    """,
                    (employee_id, year, period, window_start, window_end),
                )
                created_count += 1
                affected_employee_ids.add(employee_id)

        conn.commit()
    finally:
        conn.close()

    return {"created": created_count, "employees_affected": len(affected_employee_ids)}


# =========================================================
# Logging recognition + auto-matching to a slot
# =========================================================
def log_recognition(
    employee_id: int,
    recognition_type: str,
    date_given: str,
    title: str = None,
    description: str = None,
    submitted_by_manager_id: int = None,
    status: str = "given",
) -> dict:
    """
    Inserts a recognition_log entry, then attempts to auto-match it to
    a recognition_schedule slot for that employee/year:
      1. If the current quarter's slot is 'pending', fulfill that one.
      2. Otherwise, fulfill the earliest still-'pending' slot this year.
      3. If no pending slots remain, leave it unmatched.

    Returns {"recognition_id": int, "matched_period": str or None}.
    """
    year = int(date_given[:4])  # date_given is 'YYYY-MM-DD'

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO recognition_log
                (employee_id, recognition_type, title, description,
                 date_given, submitted_by_manager_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (employee_id, recognition_type, title, description,
             date_given, submitted_by_manager_id, status),
        )
        recognition_id = cursor.lastrowid

        this_quarter = current_quarter()

        # Try the current quarter first, if it's pending
        current_slot = conn.execute(
            """
            SELECT schedule_id FROM recognition_schedule
            WHERE employee_id = ? AND year = ? AND period = ? AND status = 'pending'
            """,
            (employee_id, year, this_quarter),
        ).fetchone()

        target_slot = current_slot

        # Otherwise, fall back to the earliest pending slot this year
        if target_slot is None:
            target_slot = conn.execute(
                """
                SELECT schedule_id, period FROM recognition_schedule
                WHERE employee_id = ? AND year = ? AND status = 'pending'
                ORDER BY period ASC
                LIMIT 1
                """,
                (employee_id, year),
            ).fetchone()

        matched_period = None
        if target_slot is not None:
            conn.execute(
                """
                UPDATE recognition_schedule
                SET status = 'fulfilled', fulfilled_by_recognition_id = ?
                WHERE schedule_id = ?
                """,
                (recognition_id, target_slot["schedule_id"]),
            )
            matched_period = target_slot["period"] if "period" in target_slot.keys() else this_quarter

        conn.commit()
    finally:
        conn.close()

    return {"recognition_id": recognition_id, "matched_period": matched_period}


# =========================================================
# Read queries
# =========================================================
def get_recognition_history(employee_id: int):
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT recognition_id, recognition_type, title, description,
                   date_given, status
            FROM recognition_log
            WHERE employee_id = ?
            ORDER BY date_given DESC
            """,
            (employee_id,),
        ).fetchall()
    finally:
        conn.close()


def get_quarterly_status_for_team(manager_id: int, year: int):
    """
    Returns one row per employee showing fulfilled count and per-quarter
    status, for the team-wide recognition compliance view.
    """
    conn = get_connection()
    try:
        employees = conn.execute(
            """
            SELECT employee_id, first_name, last_name
            FROM employees
            WHERE manager_id = ? AND is_deleted = 0 AND employment_status = 'active'
            ORDER BY last_name, first_name
            """,
            (manager_id,),
        ).fetchall()

        results = []
        for emp in employees:
            slots = conn.execute(
                """
                SELECT period, status
                FROM recognition_schedule
                WHERE employee_id = ? AND year = ?
                ORDER BY period ASC
                """,
                (emp["employee_id"], year),
            ).fetchall()

            slot_map = {s["period"]: s["status"] for s in slots}
            fulfilled_count = sum(1 for s in slot_map.values() if s == "fulfilled")

            results.append({
                "employee_id": emp["employee_id"],
                "first_name": emp["first_name"],
                "last_name": emp["last_name"],
                "fulfilled_count": fulfilled_count,
                "q1": slot_map.get("Q1", "-"),
                "q2": slot_map.get("Q2", "-"),
                "q3": slot_map.get("Q3", "-"),
                "q4": slot_map.get("Q4", "-"),
            })

        return results
    finally:
        conn.close()