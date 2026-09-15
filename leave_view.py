"""
leave_view.py
Two-part leave screen:
  1. Team-wide "who's out" list, grouped by date (7 days back, 30 ahead)
  2. Per-employee leave history (select an employee to see their records,
     split into upcoming vs past)

Usage from main.py:
    from leave_view import LeaveViewFrame
    LeaveViewFrame(self.content, session=self.session, on_log_leave=self.show_log_leave)
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, datetime
from collections import defaultdict

from create_user import get_all_employees
from leave_queries import get_team_leave_grouped, get_leave_for_employee, calculate_hours


class LeaveViewFrame(ttk.Frame):
    def __init__(self, parent, session, on_log_leave=None):
        super().__init__(parent)
        self.session = session
        self.on_log_leave = on_log_leave

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Leave", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Log Leave", command=self._handle_log_leave).pack(side="right")

        # Split into two columns: team view (left) and per-employee view (right)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=(0, 0, 16, 0))
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(body, padding=(16, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)

        self._build_team_section(left)
        self._build_employee_section(right)

    # -----------------------------------------------------
    # Team "who's out" section, grouped by date
    # -----------------------------------------------------
    def _build_team_section(self, parent):
        ttk.Label(parent, text="Team  Who's Out (past 7 / next 30 days)",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))

        records = get_team_leave_grouped(self.session.manager_id)

        if not records:
            ttk.Label(parent, text="No approved leave in this window.", foreground="gray").pack(
                anchor="w"
            )
            return

        # Group by the start date (date portion only)
        grouped = defaultdict(list)
        for r in records:
            day = r["start_datetime"].split(" ")[0]  # 'YYYY-MM-DD'
            grouped[day].append(r)

        today_str = date.today().isoformat()

        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill="both", expand=True)

        for day in sorted(grouped.keys()):
            day_label = day + ("  (today)" if day == today_str else "")
            day_frame = ttk.Frame(canvas_frame, padding=(0, 4))
            day_frame.pack(fill="x", anchor="w")

            ttk.Label(day_frame, text=day_label, font=("Segoe UI", 9, "bold")).pack(anchor="w")

            for r in grouped[day]:
                name = f"{r['first_name']} {r['last_name']}"
                start_t = r["start_datetime"].split(" ")[1] if " " in r["start_datetime"] else ""
                end_t = r["end_datetime"].split(" ")[1] if " " in r["end_datetime"] else ""
                text = f"    {name} - {r['leave_type']} ({start_t}-{end_t})"
                ttk.Label(day_frame, text=text, foreground="gray").pack(anchor="w")

    # -----------------------------------------------------
    # Per-employee leave history section
    # -----------------------------------------------------
    def _build_employee_section(self, parent):
        ttk.Label(parent, text="Employee Leave History", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        self.employees = get_all_employees(manager_id=self.session.manager_id)
        self.employee_display_to_id = {
            f"{e['first_name']} {e['last_name']}": e["employee_id"] for e in self.employees
        }

        picker_frame = ttk.Frame(parent)
        picker_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(picker_frame, text="Employee:").pack(side="left", padx=(0, 8))
        self.employee_var = tk.StringVar()
        employee_names = list(self.employee_display_to_id.keys())
        combo = ttk.Combobox(
            picker_frame, textvariable=self.employee_var, values=employee_names,
            width=28, state="readonly"
        )
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_employee_history())

        self.history_container = ttk.Frame(parent)
        self.history_container.pack(fill="both", expand=True)

        if employee_names:
            self.employee_var.set(employee_names[0])
            self._refresh_employee_history()

    def _refresh_employee_history(self):
        for widget in self.history_container.winfo_children():
            widget.destroy()

        choice = self.employee_var.get()
        if not choice:
            return
        employee_id = self.employee_display_to_id[choice]

        records = get_leave_for_employee(employee_id)

        if not records:
            ttk.Label(self.history_container, text="No leave records for this employee.",
                      foreground="gray").pack(anchor="w")
            return

        today_str = date.today().isoformat()
        upcoming = [r for r in records if r["start_datetime"].split(" ")[0] >= today_str]
        past = [r for r in records if r["start_datetime"].split(" ")[0] < today_str]

        # Total hours used (approved, past) - a simple running total
        approved_past_hours = sum(
            calculate_hours(r["start_datetime"], r["end_datetime"])
            for r in past if r["status"] == "approved"
        )
        ttk.Label(
            self.history_container,
            text=f"Approved hours used to date: {approved_past_hours}",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        self._build_leave_table(self.history_container, "Upcoming / Projected", upcoming)
        self._build_leave_table(self.history_container, "Past", past)

    def _build_leave_table(self, parent, title, records):
        section = ttk.Frame(parent, padding=(0, 0, 0, 12))
        section.pack(fill="x", anchor="n")

        ttk.Label(section, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")

        if not records:
            ttk.Label(section, text="None.", foreground="gray").pack(anchor="w", pady=(4, 0))
            return

        columns = ("Type", "Start", "End", "Hours", "Status")
        tree = ttk.Treeview(section, columns=columns, show="headings", height=min(len(records), 6))
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="w")

        for r in records:
            hours = calculate_hours(r["start_datetime"], r["end_datetime"])
            tree.insert("", "end", values=(
                r["leave_type"], r["start_datetime"], r["end_datetime"], hours, r["status"]
            ))
        tree.pack(fill="x", pady=(4, 0))

    # -----------------------------------------------------
    def _handle_log_leave(self):
        if self.on_log_leave:
            self.on_log_leave()
