"""
main.py
App entry point. Shows the login screen first; on success, opens the
main window (sidebar nav + dashboard) with a Session object carrying
the logged-in manager's info.

Run:
    python main.py

Expects in the same folder:
    db.py, session.py, auth.py, auth_manager.py, dashboard_queries.py,
    PyVA_db.db (already built from schema.sql)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from auth_manager import authenticate, update_last_login
from session import Session
from dashboard_queries import (
    get_overdue_reviews,
    get_upcoming_reviews,
    get_recognition_gaps,
    get_upcoming_wgi_dates,
    get_team_summary,
)
from employee_form import EmployeeFormFrame
from employee_list import EmployeeListFrame
from leave_view import LeaveViewFrame
from leave_form import LogLeaveFrame


# =========================================================
# Login window
# =========================================================
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PyVA — Log In")
        self.geometry("360x260")
        self.resizable(False, False)

        container = ttk.Frame(self, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="PyVA Management", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20)
        )

        ttk.Label(container, text="Username").grid(row=1, column=0, sticky="w", pady=5)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(container, textvariable=self.username_var, width=26)
        username_entry.grid(row=1, column=1, pady=5)
        username_entry.focus()

        ttk.Label(container, text="Password").grid(row=2, column=0, sticky="w", pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(container, textvariable=self.password_var, show="*", width=26)
        password_entry.grid(row=2, column=1, pady=5)
        password_entry.bind("<Return>", lambda e: self.handle_login())

        ttk.Button(container, text="Log In", command=self.handle_login).grid(
            row=3, column=0, columnspan=2, pady=(20, 5), sticky="ew"
        )

        self.status_label = ttk.Label(container, text="", foreground="red", wraplength=300)
        self.status_label.grid(row=4, column=0, columnspan=2, pady=10)

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            self.status_label.config(text="Enter both username and password.")
            return

        manager = authenticate(username, password)
        if manager is None:
            self.status_label.config(text="Invalid username or password.")
            return

        update_last_login(manager["manager_id"])
        session = Session.from_row(manager)

        self.destroy()
        app = MainWindow(session)
        app.mainloop()


# =========================================================
# Main application window (post-login)
# =========================================================
class MainWindow(tk.Tk):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.title(f"PyVA Management — {session.full_name}")
        self.geometry("900x600")
        self.minsize(760, 500)

        self._build_layout()
        self.show_dashboard()

    def _build_layout(self):
        # Top bar: who's logged in
        topbar = ttk.Frame(self, padding=(12, 8))
        topbar.pack(side="top", fill="x")
        ttk.Label(
            topbar,
            text=f"Logged in as {self.session.full_name} ({self.session.role})",
            font=("Segoe UI", 9),
        ).pack(side="left")
        ttk.Button(topbar, text="Log Out", command=self.handle_logout).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(side="top", fill="x")

        body = ttk.Frame(self)
        body.pack(side="top", fill="both", expand=True)

        # Sidebar nav
        sidebar = ttk.Frame(body, padding=10, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        nav_buttons = [
            ("Dashboard", self.show_dashboard),
            ("Employees", self.show_employee_list),
            ("Leave", self.show_leave_view),
            ("Compliance Reviews", self.show_placeholder("Compliance Reviews")),
            ("Recognition", self.show_placeholder("Recognition")),
            ("Notes", self.show_placeholder("Notes")),
        ]
        for label, cmd in nav_buttons:
            ttk.Button(sidebar, text=label, command=cmd).pack(fill="x", pady=3)

        ttk.Separator(body, orient="vertical").pack(side="left", fill="y")

        # Main content area — screens will clear/rebuild this frame
        self.content = ttk.Frame(body, padding=16)
        self.content.pack(side="left", fill="both", expand=True)

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_placeholder(self, name):
        def _show():
            self._clear_content()
            ttk.Label(
                self.content, text=f"{name} screen — coming soon", font=("Segoe UI", 12)
            ).pack(anchor="w")
        return _show

    def show_add_employee(self):
        self._clear_content()
        form = EmployeeFormFrame(self.content, session=self.session, on_saved=self.show_employee_list)
        form.pack(fill="both", expand=True)

    def show_edit_employee(self, employee_id):
        self._clear_content()
        form = EmployeeFormFrame(
            self.content, session=self.session, employee_id=employee_id,
            on_saved=self.show_employee_list,
        )
        form.pack(fill="both", expand=True)

    def show_employee_list(self):
        self._clear_content()
        listing = EmployeeListFrame(
            self.content, session=self.session,
            on_add=self.show_add_employee,
            on_edit=self.show_edit_employee,
        )
        listing.pack(fill="both", expand=True)

    def show_leave_view(self):
        self._clear_content()
        view = LeaveViewFrame(
            self.content, session=self.session,
            on_log_leave=self.show_log_leave,
        )
        view.pack(fill="both", expand=True)

    def show_log_leave(self):
        self._clear_content()
        form = LogLeaveFrame(self.content, session=self.session, on_saved=self.show_leave_view)
        form.pack(fill="both", expand=True)

    def show_dashboard(self):
        self._clear_content()
        manager_id = self.session.manager_id
        this_year = date.today().year

        ttk.Label(self.content, text="Dashboard", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        # --- Team summary tile ---
        summary = get_team_summary(manager_id)
        ttk.Label(
            self.content,
            text=f"Active team members: {summary['active_employees']}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 16))

        # --- Overdue compliance reviews ---
        self._build_section(
            title="Overdue Compliance Reviews",
            rows=get_overdue_reviews(manager_id),
            columns=("Employee", "Review Type", "Scheduled Date"),
            row_mapper=lambda r: (
                f"{r['first_name']} {r['last_name']}",
                r["review_type_name"],
                r["scheduled_date"],
            ),
            empty_text="No overdue reviews. Nice work.",
        )

        # --- Upcoming compliance reviews ---
        self._build_section(
            title="Upcoming Reviews (next 14 days)",
            rows=get_upcoming_reviews(manager_id),
            columns=("Employee", "Review Type", "Scheduled Date"),
            row_mapper=lambda r: (
                f"{r['first_name']} {r['last_name']}",
                r["review_type_name"],
                r["scheduled_date"],
            ),
            empty_text="Nothing scheduled in the next 14 days.",
        )

        # --- Recognition gaps ---
        self._build_section(
            title=f"Recognition Gaps ({this_year}) — under 2 for the year",
            rows=get_recognition_gaps(manager_id, this_year),
            columns=("Employee", "Fulfilled This Year"),
            row_mapper=lambda r: (
                f"{r['first_name']} {r['last_name']}",
                f"{r['fulfilled_count']} of 2",
            ),
            empty_text="Everyone is on pace for recognition this year.",
        )

        # --- Upcoming WGI dates ---
        self._build_section(
            title="Upcoming Within-Grade Increases (next 60 days)",
            rows=get_upcoming_wgi_dates(manager_id),
            columns=("Employee", "Next WGI Date"),
            row_mapper=lambda r: (
                f"{r['first_name']} {r['last_name']}",
                r["next_wgi_date"],
            ),
            empty_text="No WGI dates coming up in the next 60 days.",
        )

    def _build_section(self, title, rows, columns, row_mapper, empty_text):
        section = ttk.Frame(self.content, padding=(0, 0, 0, 16))
        section.pack(fill="x", anchor="n")

        ttk.Label(section, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w")

        if not rows:
            ttk.Label(section, text=empty_text, foreground="gray").pack(anchor="w", pady=(4, 0))
            return

        tree = ttk.Treeview(section, columns=columns, show="headings", height=min(len(rows), 6))
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200, anchor="w")
        for r in rows:
            tree.insert("", "end", values=row_mapper(r))
        tree.pack(fill="x", pady=(4, 0))

    def handle_logout(self):
        if messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            self.destroy()
            login = LoginWindow()
            login.mainloop()


if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()