"""
recognition_form.py
A form for logging a recognition entry (thank-you note, formal award,
etc.) against one employee. Auto-matches to a quarterly schedule slot
on save.

Usage:
    from recognition_form import LogRecognitionFrame
    LogRecognitionFrame(self.content, session=self.session, on_saved=self.show_recognition_view)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from create_user import get_all_employees
from recognition_queries import log_recognition


class LogRecognitionFrame(ttk.Frame):
    RECOGNITION_TYPES = ["thank_you_note", "formal_award", "spot_bonus", "other"]
    STATUSES = ["draft", "submitted", "approved", "given", "denied"]

    def __init__(self, parent, session, on_saved=None):
        super().__init__(parent)
        self.session = session
        self.on_saved = on_saved

        self.employees = get_all_employees(manager_id=session.manager_id)
        self.employee_display_to_id = {
            f"{e['first_name']} {e['last_name']}": e["employee_id"] for e in self.employees
        }

        ttk.Label(self, text="Log Recognition", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", pady=(0, 16)
        )

        form = ttk.Frame(self)
        form.pack(anchor="w")

        row = 0
        ttk.Label(form, text="Employee *").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.employee_var = tk.StringVar()
        ttk.Combobox(
            form, textvariable=self.employee_var,
            values=list(self.employee_display_to_id.keys()),
            width=30, state="readonly"
        ).grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(form, text="Type *").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.type_var = tk.StringVar(value=self.RECOGNITION_TYPES[0])
        ttk.Combobox(
            form, textvariable=self.type_var, values=self.RECOGNITION_TYPES,
            width=30, state="readonly"
        ).grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(form, text="Title").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var, width=32).grid(
            row=row, column=1, pady=5, sticky="w"
        )
        row += 1

        ttk.Label(form, text="Date Given (YYYY-MM-DD) *").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(form, textvariable=self.date_var, width=32).grid(
            row=row, column=1, pady=5, sticky="w"
        )
        row += 1

        ttk.Label(form, text="Status").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        self.status_var = tk.StringVar(value="given")
        ttk.Combobox(
            form, textvariable=self.status_var, values=self.STATUSES,
            width=30, state="readonly"
        ).grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(form, text="Description / Note").grid(
            row=row, column=0, sticky="nw", pady=5, padx=(0, 10)
        )
        self.description_text = tk.Text(form, width=32, height=5)
        self.description_text.grid(row=row, column=1, pady=5, sticky="w")
        row += 1

        ttk.Label(
            self, text="* Required fields", foreground="gray", font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(4, 0))

        footer = ttk.Frame(self, padding=(0, 16, 0, 0))
        footer.pack(fill="x")
        self.status_label = ttk.Label(footer, text="", foreground="red", wraplength=400)
        self.status_label.pack(side="left")
        ttk.Button(footer, text="Save Recognition", command=self.handle_save).pack(side="right")

    def handle_save(self):
        employee_choice = self.employee_var.get()
        if not employee_choice:
            self.status_label.config(text="Select an employee.")
            return
        employee_id = self.employee_display_to_id[employee_choice]

        date_given = self.date_var.get().strip()
        if not date_given:
            self.status_label.config(text="Date given is required.")
            return

        title = self.title_var.get().strip() or None
        description = self.description_text.get("1.0", "end").strip() or None

        try:
            result = log_recognition(
                employee_id=employee_id,
                recognition_type=self.type_var.get(),
                date_given=date_given,
                title=title,
                description=description,
                submitted_by_manager_id=self.session.manager_id,
                status=self.status_var.get(),
            )
        except (ValueError, IndexError):
            self.status_label.config(text="Could not parse date. Use YYYY-MM-DD.")
            return

        self.status_label.config(text="", foreground="red")

        if result["matched_period"]:
            messagebox.showinfo(
                "Saved",
                f"Recognition logged and matched to {result['matched_period']}.",
            )
        else:
            messagebox.showinfo(
                "Saved",
                "Recognition logged. All quarters this year are already fulfilled "
                "for this employee, so it wasn't matched to a slot.",
            )

        if self.on_saved:
            self.on_saved()