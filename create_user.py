"""
create_user.py
Functions to create a new manager (login account) or a new employee
(team member record, no login) in PyVA_db.db.

Can be run directly for an interactive prompt, or imported and called
from other scripts / the Tkinter app.

    python create_user.py
"""

import sqlite3
from db import get_connection
from auth import hash_password


# =========================================================
# Manager creation
# =========================================================
def create_manager(
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = "manager",
) -> int:
    """
    Creates a new manager (login) account. Password is hashed before
    storage. Returns the new manager_id.

    Raises sqlite3.IntegrityError if username or email is already taken.
    Raises ValueError if role is not 'admin' or 'manager'.
    """
    if role not in ("admin", "manager"):
        raise ValueError("role must be 'admin' or 'manager'")

    pw_hash = hash_password(password)

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO managers (username, email, password_hash, first_name, last_name, role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, pw_hash, first_name, last_name, role),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# =========================================================
# Employee creation
# =========================================================
def create_employee(
    manager_id: int,
    first_name: str,
    last_name: str,
    assistant_manager_id: int = None,
    preferred_name: str = None,
    birthday: str = None,
    work_email: str = None,
    personal_email: str = None,
    phone_number: str = None,
    mailing_address_line1: str = None,
    mailing_address_line2: str = None,
    city: str = None,
    state: str = None,
    zip_code: str = None,
    position_title: str = None,
    grade: str = None,
    step: str = None,
    hire_date: str = None,
    time_in_grade_date: str = None,
    next_wgi_date: str = None,
    promotion_eligible_date: str = None,
    last_promotion_date: str = None,
) -> int:
    """
    Creates a new employee record under the given manager. No login
    credentials involved - employees don't log into this app.
    Returns the new employee_id.

    Raises sqlite3.IntegrityError on foreign key issues (e.g. bad manager_id).
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO employees (
                manager_id, assistant_manager_id, first_name, last_name,
                preferred_name, birthday,
                work_email, personal_email, phone_number,
                mailing_address_line1, mailing_address_line2, city, state, zip_code,
                position_title, grade, step, hire_date,
                time_in_grade_date, next_wgi_date,
                promotion_eligible_date, last_promotion_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manager_id, assistant_manager_id, first_name, last_name,
                preferred_name, birthday,
                work_email, personal_email, phone_number,
                mailing_address_line1, mailing_address_line2, city, state, zip_code,
                position_title, grade, step, hire_date,
                time_in_grade_date, next_wgi_date,
                promotion_eligible_date, last_promotion_date,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# =========================================================
# Employee read / update / deactivate
# =========================================================
def get_all_employees(manager_id: int = None):
    """
    Returns all active (not deleted) employees, optionally filtered to
    one manager. Used to populate the roster/list view.
    """
    conn = get_connection()
    try:
        if manager_id is not None:
            return conn.execute(
                """
                SELECT employee_id, first_name, last_name, position_title,
                       employment_status, hire_date, preferred_name
                FROM employees
                WHERE is_deleted = 0 AND manager_id = ?
                ORDER BY last_name, first_name
                """,
                (manager_id,),
            ).fetchall()
        return conn.execute(
            """
            SELECT employee_id, first_name, last_name, position_title,
                   employment_status, hire_date
            FROM employees
            WHERE is_deleted = 0
            ORDER BY last_name, first_name
            """
        ).fetchall()
    finally:
        conn.close()


def get_employee_by_id(employee_id: int):
    """Returns the full row for one employee, or None if not found/deleted."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM employees WHERE employee_id = ? AND is_deleted = 0",
            (employee_id,),
        ).fetchone()
    finally:
        conn.close()


def update_employee(employee_id: int, **fields) -> None:
    """
    Updates the given employee with whatever fields are passed as
    keyword arguments, e.g.:
        update_employee(5, first_name="Jane", grade="GS-12")

    Only columns explicitly passed are touched; anything not passed
    is left as-is. Raises sqlite3.IntegrityError on constraint issues.
    """
    if not fields:
        return  # nothing to update

    allowed_columns = {
        "manager_id", "assistant_manager_id", "first_name", "last_name",
        "preferred_name", "birthday",
        "work_email", "personal_email", "phone_number",
        "mailing_address_line1", "mailing_address_line2", "city", "state", "zip_code",
        "position_title", "grade", "step", "hire_date",
        "time_in_grade_date", "next_wgi_date",
        "promotion_eligible_date", "last_promotion_date",
        "employment_status",
    }

    # Filter out anything not a real column, to avoid SQL injection via kwargs
    # and to fail loudly on typos rather than silently ignoring them.
    unknown = set(fields.keys()) - allowed_columns
    if unknown:
        raise ValueError(f"update_employee got unknown field(s): {unknown}")

    set_clause = ", ".join(f"{col} = ?" for col in fields.keys())
    values = list(fields.values()) + [employee_id]

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE employees SET {set_clause} WHERE employee_id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()


def deactivate_employee(employee_id: int) -> None:
    """
    Soft-deletes an employee (sets is_deleted = 1) rather than removing
    the row, so their leave/review/recognition history is preserved.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE employees SET is_deleted = 1 WHERE employee_id = ?",
            (employee_id,),
        )
        conn.commit()
    finally:
        conn.close()
# =========================================================
def _prompt_create_manager():
    print("\n--- Create Manager ---")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    role = input("Role [manager/admin] (default manager): ").strip() or "manager"

    try:
        manager_id = create_manager(username, email, password, first_name, last_name, role)
        print(f"Manager created with manager_id = {manager_id}")
    except sqlite3.IntegrityError:
        print("Error: that username or email is already in use.")
    except ValueError as e:
        print(f"Error: {e}")


def _prompt_create_employee():
    print("\n--- Create Employee ---")
    try:
        manager_id = int(input("Manager ID this employee reports to: ").strip())
    except ValueError:
        print("Error: manager ID must be a number.")
        return

    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    position_title = input("Position title (optional): ").strip() or None
    hire_date = input("Hire date YYYY-MM-DD (optional): ").strip() or None

    try:
        employee_id = create_employee(
            manager_id=manager_id,
            first_name=first_name,
            last_name=last_name,
            position_title=position_title,
            hire_date=hire_date,
        )
        print(f"Employee created with employee_id = {employee_id}")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("What would you like to create?")
    print("1. Manager (login account)")
    print("2. Employee (team member record)")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        _prompt_create_manager()
    elif choice == "2":
        _prompt_create_employee()
    else:
        print("Invalid choice.")