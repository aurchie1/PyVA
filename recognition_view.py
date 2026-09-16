"""
recognition_view.py
Recognition screen: team-wide quarterly compliance grid (who's fulfilled
Q1-Q4 this year) plus a per-employee recognition history panel.

Usage from main.py:
    from recognition_view import RecognitionViewFrame
    RecognitionViewFrame(self.content, session=self.session, on_log_recognition=self.show_log_recognition)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from create_user import get_all_employees
from recognition_queries import (
    get_quarterly_status_for_team,
    get_recognition_history,
    generate_quarterly_slots,
)


class RecognitionViewFrame(ttk.Frame):
    def __init__(self, parent, session, on_log_recognition=None):
        super().__init__(parent)
        self.session = session
        self.on_log_recognition = on_log_recognition
        self.year = date.today().year

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text=f"Recognition ({self.year})", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ttk.Button(header, text="Log Recognition", command=self._handle_log).pack(side="right")
        ttk.Button(header, text="Generate This Year's Slots", command=self.handle_generate_slots).pack(
            side="right", padx=(0, 8)
        )

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=(0, 0, 16, 0))
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(body, padding=(16, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)

        self._build_team_section(left)
        self._build_employee_section(right)

    # -----------------------------------------------------
    # Team-wide quarterly status grid
    # -----------------------------------------------------
    def _build_team_section(self, parent):
        ttk.Label(parent, text="Team Quarterly Status", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        self.team_tree_container = parent
        self._refresh_team_grid()

    def _refresh_team_grid(self):
        for widget in self.team_tree_container.winfo_children():
            if isinstance(widget, ttk.Treeview) or isinstance(widget, ttk.Label) and widget.cget("text") != "Team Quarterly Status":
                widget.destroy()

        rows = get_quarterly_status_for_team(self.session.manager_id, self.year)

        if not rows:
            ttk.Label(self.team_tree_container, text="No active employees.", foreground="gray").pack(
                anchor="w"
            )
            return

        columns = ("Employee", "Q1", "Q2", "Q3", "Q4", "Fulfilled")
        tree = ttk.Treeview(self.team_tree_container, columns=columns, show="headings", height=len(rows))
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=90 if col != "Employee" else 160, anchor="center")

        for r in rows:
            name = f"{r['first_name']} {r['last_name']}"
            fulfilled_text = f"{r['fulfilled_count']} of 2+"
            tags = ("under",) if r["fulfilled_count"] < 2 else ()
            tree.insert(
                "", "end",
                values=(name, r["q1"], r["q2"], r["q3"], r["q4"], fulfilled_text),
                tags=tags,
            )

        tree.tag_configure("under", background="#fff3cd")  # light yellow highlight
        tree.pack(fill="both", expand=True)

    def handle_generate_slots(self):
        confirmed = messagebox.askyesno(
            "Generate Quarterly Slots",
            f"Create the {self.year} Q1-Q4 recognition slots for any active employee "
            f"who doesn't already have them? Existing slots are left untouched.",
        )
        if not confirmed:
            return

        result = generate_quarterly_slots(self.year)
        messagebox.showinfo(
            "Done",
            f"Created {result['created']} slot(s) across {result['employees_affected']} employee(s).",
        )
        self._refresh_team_grid()

    # -----------------------------------------------------
    # Per-employee recognition history
    # -----------------------------------------------------
    def _build_employee_section(self, parent):
        ttk.Label(parent, text="Recognition History", font=("Segoe UI", 11, "bold")).pack(
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
        combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_history())

        self.history_container = ttk.Frame(parent)
        self.history_container.pack(fill="both", expand=True)

        if employee_names:
            self.employee_var.set(employee_names[0])
            self._refresh_history()

    def _refresh_history(self):
        for widget in self.history_container.winfo_children():
            widget.destroy()

        choice = self.employee_var.get()
        if not choice:
            return
        employee_id = self.employee_display_to_id[choice]

        records = get_recognition_history(employee_id)

        if not records:
            ttk.Label(self.history_container, text="No recognition logged yet.", foreground="gray").pack(
                anchor="w"
            )
            return

        columns = ("Date", "Type", "Title", "Status")
        tree = ttk.Treeview(
            self.history_container, columns=columns, show="headings",
            height=min(len(records), 10)
        )
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="w")

        for r in records:
            tree.insert("", "end", values=(
                r["date_given"], r["recognition_type"], r["title"] or "", r["status"]
            ))
        tree.pack(fill="both", expand=True)

    # -----------------------------------------------------
    def _handle_log(self):
        if self.on_log_recognition:
            self.on_log_recognition()
