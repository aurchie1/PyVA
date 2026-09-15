# -*- coding: utf-8 -*-
"""
session.py
Holds the currently logged-in manager's info so any screen in the app
can check who's using it without re-querying the database each time.
"""

from dataclasses import dataclass


@dataclass
class Session:
    manager_id: int
    username: str
    first_name: str
    last_name: str
    role: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @classmethod
    def from_row(cls, row) -> "Session":
        """Build a Session from a sqlite3.Row (e.g. the result of authenticate())."""
        return cls(
            manager_id=row["manager_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            role=row["role"],
        )
