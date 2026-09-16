"""
review_type_queries.py
CRUD functions for review_types: the definitions that drive
auto-scheduling (name, frequency, frequency_unit, active flag).
"""

import sqlite3
from db import get_connection

VALID_UNITS = ("days", "weeks", "months")


def get_all_review_types(include_inactive: bool = True):
    conn = get_connection()
    try:
        if include_inactive:
            return conn.execute(
                "SELECT * FROM review_types ORDER BY name"
            ).fetchall()
        return conn.execute(
            "SELECT * FROM review_types WHERE is_active = 1 ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def get_review_type_by_id(review_type_id: int):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM review_types WHERE review_type_id = ?",
            (review_type_id,),
        ).fetchone()
    finally:
        conn.close()


def create_review_type(name: str, frequency: int, frequency_unit: str, description: str = None) -> int:
    """
    Creates a new review type. Raises ValueError for bad input, or
    sqlite3.IntegrityError if the name already exists (UNIQUE constraint).
    """
    if frequency_unit not in VALID_UNITS:
        raise ValueError(f"frequency_unit must be one of {VALID_UNITS}")
    if frequency <= 0:
        raise ValueError("frequency must be a positive number")

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO review_types (name, description, frequency, frequency_unit)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, frequency, frequency_unit),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_review_type(
    review_type_id: int,
    name: str,
    frequency: int,
    frequency_unit: str,
    description: str = None,
) -> None:
    """
    Updates an existing review type's name/frequency/description.
    Does NOT touch already-scheduled compliance_reviews rows - only
    future auto-generated reviews will use the new frequency.
    """
    if frequency_unit not in VALID_UNITS:
        raise ValueError(f"frequency_unit must be one of {VALID_UNITS}")
    if frequency <= 0:
        raise ValueError("frequency must be a positive number")

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE review_types
            SET name = ?, description = ?, frequency = ?, frequency_unit = ?
            WHERE review_type_id = ?
            """,
            (name, description, frequency, frequency_unit, review_type_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_review_type_active(review_type_id: int, is_active: bool) -> None:
    """
    Activates or deactivates a review type. Deactivating stops it from
    being used for schedule_initial_reviews on new employees, but does
    not touch existing scheduled/completed reviews of this type.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE review_types SET is_active = ? WHERE review_type_id = ?",
            (1 if is_active else 0, review_type_id),
        )
        conn.commit()
    finally:
        conn.close()