"""
leave_form.py
A form for logging a new leave record against one employee.

Usage from main.py or leave_view.py:
    from leave_form import LogLeaveFrame
    LogLeaveFrame(self.content, session=self.session, on_saved=self.show_leave_view)
"""

import tkinter as tk
from tkinter import ttk, messagebox

from create_user import get_all_employees
from leave_queries import create_leave_record, calculate_hours


class LogLeaveFrame(ttk.Frame):
    """
    Args:
        parent: the Tkinter container to place this frame in
        session: the current Session (used to scope employee list + logged_by)
        on_saved: optional callback invoked after a successful save
    """

    LEAVE_TYPES = ["annual", "sick", "fmla", "admin", "unpaid", "other"]
    STATUSES = ["pending", "approved", "denied", "cancelled"]

    def __init__(self, parent, session, on_saved=None):
        super().__init__(parent)
        self.session = session
        self.on_saved = on_saved

        self.employees = get_all_employees(manager_id=session.manager_id)
        self.employee_display_to_id = {
            f"{e['first_name']} {e['last_name']}": e["employee_id"] for e in self.employees
        }

        ttk.Label(self, text="Log Leave", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", pady=(0, 16)
        )

        form = ttk.Frame(self)
        form.pack(anchor="w")

        row = 0
        ttk.Label(form, text="Employee *").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.employee_var = tk.StringVar()
        employee_names = list(self.employee_display_to_id.keys())
        ttk.Combobox(
            form, textvariable=self.employee_var, values=employee_names,
            width=30, state="readonly"
        ).grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(form, text="Leave Type *").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.leave_type_var = tk.StringVar(value=self.LEAVE_TYPES[0])
        ttk.Combobox(
            form, textvariable=self.leave_type_var, values=self.LEAVE_TYPES,
            width=30, state="readonly"
        ).grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(form, text="Start Date (YYYY-MM-DD) *").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        self.start_date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.start_date_var, width=32).grid(
            row=row, column=1, pady=5, sticky="w"
        )
        row += 1

        ttk.Label(form, text="Start Time (HH:MM, 24hr) *").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        self.start_time_var = tk.StringVar(value="08:00")
        ttk.Entry(form, textvariable=self.start_time_var, width=32).grid(
            row=row, column=1, pady=5, sticky="w"
        )
        row += 1

        ttk.Label(form, text="End Date (YYYY-MM-DD) *").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        self.end_date_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.end_date_var, width=32).grid(
            row=row, column=1, pady=5, sticky="w"
        )
        row += 1

        ttk.Label(form, text="End Time (HH:MM, 24hr) *").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        self.end_time_var = tk.StringVar(value="17:00")
        ttk.Entry(form, textvariable=self.end_time_var, width=32).grid(
            row=row, column=1, pady=5, sticky="w"
        )
        row += 1

        ttk.Label(form, text="Status").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.status_var = tk.StringVar(value="approved")
        ttk.Combobox(
            form, textvariable=self.status_var, values=self.STATUSES,
            width=30, state="readonly"
        ).grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(form, text="Notes").grid(row=row, column=0, sticky="nw", pady=5, padx=(0, 10))
        self.notes_text = tk.Text(form, width=32, height=4)
        self.notes_text.grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(
            self, text="* Required fields", foreground="gray", font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(4, 0))

        self.hours_label = ttk.Label(self, text="", font=("Segoe UI", 9, "italic"))
        self.hours_label.pack(anchor="w", pady=(8, 0))

        footer = ttk.Frame(self, padding=(0, 16, 0, 0))
        footer.pack(fill="x")
        self.status_label = ttk.Label(footer, text="", foreground="red", wraplength=400)
        self.status_label.pack(side="left")
        ttk.Button(footer, text="Save Leave Record", command=self.handle_save).pack(side="right")
        ttk.Button(footer, text="Preview Hours", command=self.handle_preview_hours).pack(
            side="right", padx=(0, 8)
        )

    def _build_datetime(self, date_var, time_var):
        date_str = date_var.get().strip()
        time_str = time_var.get().strip()
        if not date_str or not time_str:
            return None
        return f"{date_str} {time_str}"

    def handle_preview_hours(self):
        start = self._build_datetime(self.start_date_var, self.start_time_var)
        end = self._build_datetime(self.end_date_var, self.end_time_var)

        if not start or not end:
            self.hours_label.config(text="Enter both start and end date/time to preview hours.")
            return

        try:
            hours = calculate_hours(start, end)
        except ValueError:
            self.hours_label.config(text="Could not parse dates. Use YYYY-MM-DD and HH:MM.")
            return

        self.hours_label.config(text=f"This entry = {hours} hours")

    def handle_save(self):
        employee_choice = self.employee_var.get()
        if not employee_choice:
            self.status_label.config(text="Select an employee.")
            return
        employee_id = self.employee_display_to_id[employee_choice]

        start = self._build_datetime(self.start_date_var, self.start_time_var)
        end = self._build_datetime(self.end_date_var, self.end_time_var)

        if not start or not end:
            self.status_label.config(text="Start and end date/time are required.")
            return

        try:
            hours = calculate_hours(start, end)
        except ValueError:
            self.status_label.config(text="Could not parse dates. Use YYYY-MM-DD and HH:MM.")
            return

        if hours <= 0:
            self.status_label.config(text="End must be after start.")
            return

        notes = self.notes_text.get("1.0", "end").strip() or None

        create_leave_record(
            employee_id=employee_id,
            leave_type=self.leave_type_var.get(),
            start_datetime=start,
            end_datetime=end,
            status=self.status_var.get(),
            notes=notes,
            logged_by_manager_id=self.session.manager_id,
        )

        self.status_label.config(text="", foreground="red")
        messagebox.showinfo("Saved", f"Leave record saved ({hours} hours).")

        if self.on_saved:
            self.on_saved()