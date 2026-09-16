"""
review_type_form.py
A popup dialog window for adding or editing a review type.

Usage:
    from review_type_form import ReviewTypeDialog

    # Add mode:
    ReviewTypeDialog(parent, on_saved=refresh_callback)

    # Edit mode:
    ReviewTypeDialog(parent, review_type_id=3, on_saved=refresh_callback)
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from review_type_queries import (
    create_review_type,
    update_review_type,
    get_review_type_by_id,
    VALID_UNITS,
)


class ReviewTypeDialog(tk.Toplevel):
    def __init__(self, parent, review_type_id=None, on_saved=None):
        super().__init__(parent)
        self.review_type_id = review_type_id
        self.is_edit_mode = review_type_id is not None
        self.on_saved = on_saved

        self.title("Edit Review Type" if self.is_edit_mode else "Add Review Type")
        self.geometry("380x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # modal: block interaction with the main window

        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Name *").grid(row=0, column=0, sticky="w", pady=6)
        self.name_var = tk.StringVar()
        ttk.Entry(container, textvariable=self.name_var, width=28).grid(
            row=0, column=1, pady=6, sticky="w"
        )

        ttk.Label(container, text="Description").grid(row=1, column=0, sticky="nw", pady=6)
        self.description_text = tk.Text(container, width=22, height=3)
        self.description_text.grid(row=1, column=1, pady=6, sticky="w")

        ttk.Label(container, text="Frequency *").grid(row=2, column=0, sticky="w", pady=6)
        self.frequency_var = tk.StringVar()
        ttk.Entry(container, textvariable=self.frequency_var, width=10).grid(
            row=2, column=1, pady=6, sticky="w"
        )

        ttk.Label(container, text="Unit *").grid(row=3, column=0, sticky="w", pady=6)
        self.unit_var = tk.StringVar(value="months")
        ttk.Combobox(
            container, textvariable=self.unit_var, values=list(VALID_UNITS),
            width=25, state="readonly"
        ).grid(row=3, column=1, pady=6, sticky="w")

        ttk.Label(
            container, text="* Required. E.g. Frequency=6, Unit=months means every 6 months.",
            foreground="gray", font=("Segoe UI", 8), wraplength=280
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.status_label = ttk.Label(container, text="", foreground="red", wraplength=320)
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))

        footer = ttk.Frame(container)
        footer.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(footer, text="Save", command=self.handle_save).pack(side="right", padx=(0, 8))

        if self.is_edit_mode:
            self._load_data()

    def _load_data(self):
        row = get_review_type_by_id(self.review_type_id)
        if row is None:
            self.status_label.config(text="Could not load review type.")
            return

        self.name_var.set(row["name"])
        self.description_text.insert("1.0", row["description"] or "")
        self.frequency_var.set(str(row["frequency"]))
        self.unit_var.set(row["frequency_unit"])

    def handle_save(self):
        name = self.name_var.get().strip()
        description = self.description_text.get("1.0", "end").strip() or None
        frequency_str = self.frequency_var.get().strip()
        unit = self.unit_var.get()

        if not name:
            self.status_label.config(text="Name is required.")
            return

        if not frequency_str.isdigit() or int(frequency_str) <= 0:
            self.status_label.config(text="Frequency must be a positive whole number.")
            return

        frequency = int(frequency_str)

        try:
            if self.is_edit_mode:
                update_review_type(
                    self.review_type_id, name=name, frequency=frequency,
                    frequency_unit=unit, description=description,
                )
            else:
                create_review_type(
                    name=name, frequency=frequency, frequency_unit=unit,
                    description=description,
                )
        except sqlite3.IntegrityError:
            self.status_label.config(text="A review type with that name already exists.")
            return
        except ValueError as e:
            self.status_label.config(text=str(e))
            return

        messagebox.showinfo("Saved", "Review type saved.")
        if self.on_saved:
            self.on_saved()
        self.destroy()
