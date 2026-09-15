# -*- coding: utf-8 -*-
"""
employee_form.py
A tabbed Employee form (Basic Info / Contact / HR Data), used for both
adding a new employee and editing an existing one. Meant to be embedded
inside MainWindow's content area.

Usage from main.py:
    from employee_form import EmployeeFormFrame

    # Add mode:
    EmployeeFormFrame(self.content, session=self.session, on_saved=self.show_employee_list)

    # Edit mode:
    EmployeeFormFrame(self.content, session=self.session, employee_id=5,
                       on_saved=self.show_employee_list)
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from db import get_connection
from create_user import create_employee, get_employee_by_id, update_employee, deactivate_employee


def get_all_managers():
    """Returns all active managers, for populating the assistant manager dropdown."""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT manager_id, first_name, last_name
            FROM managers
            WHERE is_active = 1 AND is_deleted = 0
            ORDER BY last_name, first_name
            """
        ).fetchall()
    finally:
        conn.close()


class EmployeeFormFrame(ttk.Frame):
    """
    Embeddable frame containing the tabbed Employee form.
    Pack/grid this into any parent container (e.g. MainWindow.content).

    Args:
        parent: the Tkinter container to place this frame in
        session: the current Session (used as the default manager_id in Add mode)
        employee_id: if provided, the form loads and edits that employee.
                     If None, the form is in "Add" mode.
        on_saved: optional callback invoked after a successful save or deactivate
    """

    FIELD_KEYS = [
        "first_name", "last_name", "preferred_name", "birthday",
        "work_email", "personal_email", "phone_number",
        "mailing_address_line1", "mailing_address_line2", "city", "state", "zip_code",
        "position_title", "grade", "step", "hire_date",
        "time_in_grade_date", "next_wgi_date",
        "promotion_eligible_date", "last_promotion_date",
    ]

    def __init__(self, parent, session, employee_id=None, on_saved=None):
        super().__init__(parent)
        self.session = session
        self.employee_id = employee_id
        self.on_saved = on_saved
        self.is_edit_mode = employee_id is not None

        # Load managers for the assistant manager dropdown
        self.managers = get_all_managers()
        self.manager_display_to_id = {
            f"{m['first_name']} {m['last_name']}": m["manager_id"] for m in self.managers
        }
        self.manager_id_to_display = {v: k for k, v in self.manager_display_to_id.items()}

        title_text = "Edit Employee" if self.is_edit_mode else "Add Employee"
        ttk.Label(self, text=title_text, font=("Segoe UI", 16, "bold")).pack(
            anchor="w", pady=(0, 12)
        )

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.vars = {}  # field_name -> tk.StringVar

        basic_tab = ttk.Frame(notebook, padding=16)
        contact_tab = ttk.Frame(notebook, padding=16)
        hr_tab = ttk.Frame(notebook, padding=16)

        notebook.add(basic_tab, text="Basic Info")
        notebook.add(contact_tab, text="Contact")
        notebook.add(hr_tab, text="HR Data")

        self._build_basic_tab(basic_tab)
        self._build_contact_tab(contact_tab)
        self._build_hr_tab(hr_tab)

        # Footer: status label + buttons
        footer = ttk.Frame(self, padding=(0, 12, 0, 0))
        footer.pack(fill="x")

        self.status_label = ttk.Label(footer, text="", foreground="red", wraplength=500)
        self.status_label.pack(side="left")

        button_text = "Save Changes" if self.is_edit_mode else "Save Employee"
        ttk.Button(footer, text=button_text, command=self.handle_save).pack(side="right")

        if self.is_edit_mode:
            ttk.Button(
                footer, text="Deactivate Employee", command=self.handle_deactivate
            ).pack(side="right", padx=(0, 8))

        # If editing, load existing data into the form now that widgets exist
        if self.is_edit_mode:
            self._load_employee_data()

    # -----------------------------------------------------
    # Tab builders
    # -----------------------------------------------------
    def _add_field(self, parent, row, label, key, widget="entry", values=None, required=False):
        """Helper to add a label + input on a grid row, tracking the var in self.vars."""
        label_text = label + (" *" if required else "")
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))

        var = tk.StringVar()
        if widget == "entry":
            entry = ttk.Entry(parent, textvariable=var, width=32)
            entry.grid(row=row, column=1, sticky="w", pady=4)
        elif widget == "combobox":
            combo = ttk.Combobox(parent, textvariable=var, values=values, width=29, state="readonly")
            combo.grid(row=row, column=1, sticky="w", pady=4)

        self.vars[key] = var

    def _build_basic_tab(self, tab):
        self._add_field(tab, 0, "First Name", "first_name", required=True)
        self._add_field(tab, 1, "Last Name", "last_name", required=True)
        self._add_field(tab, 2, "Preferred Name", "preferred_name")
        self._add_field(tab, 3, "Birthday (YYYY-MM-DD)", "birthday")

        # Assistant manager dropdown (optional)
        ttk.Label(tab, text="Assistant Manager").grid(row=4, column=0, sticky="w", pady=4, padx=(0, 10))
        assistant_names = ["(None)"] + list(self.manager_display_to_id.keys())
        self.assistant_var = tk.StringVar(value="(None)")
        ttk.Combobox(
            tab, textvariable=self.assistant_var, values=assistant_names, width=29, state="readonly"
        ).grid(row=4, column=1, sticky="w", pady=4)

        # Employment status dropdown (only meaningful in edit mode, but harmless in add mode)
        ttk.Label(tab, text="Employment Status").grid(row=5, column=0, sticky="w", pady=4, padx=(0, 10))
        self.status_var = tk.StringVar(value="active")
        ttk.Combobox(
            tab, textvariable=self.status_var,
            values=["active", "extended leave", "separated"],
            width=29, state="readonly"
        ).grid(row=5, column=1, sticky="w", pady=4)

        ttk.Label(
            tab, text="* Required fields", foreground="gray", font=("Segoe UI", 8)
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _build_contact_tab(self, tab):
        self._add_field(tab, 0, "Work Email", "work_email")
        self._add_field(tab, 1, "Personal Email", "personal_email")
        self._add_field(tab, 2, "Phone Number", "phone_number")
        self._add_field(tab, 3, "Mailing Address Line 1", "mailing_address_line1")
        self._add_field(tab, 4, "Mailing Address Line 2", "mailing_address_line2")
        self._add_field(tab, 5, "City", "city")
        self._add_field(tab, 6, "State", "state")
        self._add_field(tab, 7, "Zip Code", "zip_code")

    def _build_hr_tab(self, tab):
        self._add_field(tab, 0, "Position Title", "position_title")
        self._add_field(tab, 1, "Grade", "grade")
        self._add_field(tab, 2, "Step", "step")
        self._add_field(tab, 3, "Hire Date (YYYY-MM-DD)", "hire_date")
        self._add_field(tab, 4, "Time in Grade Date (YYYY-MM-DD)", "time_in_grade_date")
        self._add_field(tab, 5, "Next WGI Date (YYYY-MM-DD)", "next_wgi_date")
        self._add_field(tab, 6, "Promotion Eligible Date (YYYY-MM-DD)", "promotion_eligible_date")
        self._add_field(tab, 7, "Last Promotion Date (YYYY-MM-DD)", "last_promotion_date")

    # -----------------------------------------------------
    # Edit mode: load existing data into the form
    # -----------------------------------------------------
    def _load_employee_data(self):
        row = get_employee_by_id(self.employee_id)
        if row is None:
            self.status_label.config(text="Could not load employee (not found).")
            return

        for key in self.FIELD_KEYS:
            value = row[key]
            self.vars[key].set(value if value is not None else "")

        # Assistant manager dropdown
        assistant_id = row["assistant_manager_id"]
        if assistant_id and assistant_id in self.manager_id_to_display:
            self.assistant_var.set(self.manager_id_to_display[assistant_id])
        else:
            self.assistant_var.set("(None)")

        # Employment status dropdown
        self.status_var.set(row["employment_status"])

    # -----------------------------------------------------
    # Save handling (create or update)
    # -----------------------------------------------------
    def handle_save(self):
        first_name = self.vars["first_name"].get().strip()
        last_name = self.vars["last_name"].get().strip()

        if not first_name or not last_name:
            self.status_label.config(text="First name and last name are required.")
            return

        assistant_choice = self.assistant_var.get()
        assistant_manager_id = (
            None if assistant_choice == "(None)" else self.manager_display_to_id[assistant_choice]
        )

        def val(key):
            v = self.vars[key].get().strip()
            return v if v else None

        field_values = {key: val(key) for key in self.FIELD_KEYS}
        field_values["first_name"] = first_name
        field_values["last_name"] = last_name

        if self.is_edit_mode:
            try:
                update_employee(
                    self.employee_id,
                    assistant_manager_id=assistant_manager_id,
                    employment_status=self.status_var.get(),
                    **field_values,
                )
            except (sqlite3.IntegrityError, ValueError) as e:
                self.status_label.config(text=f"Could not save: {e}")
                return

            self.status_label.config(text="", foreground="red")
            messagebox.showinfo("Saved", "Employee updated.")
        else:
            try:
                employee_id = create_employee(
                    manager_id=self.session.manager_id,
                    assistant_manager_id=assistant_manager_id,
                    **field_values,
                )
            except sqlite3.IntegrityError as e:
                self.status_label.config(text=f"Could not save: {e}")
                return

            self.status_label.config(text="", foreground="red")
            messagebox.showinfo("Saved", f"Employee created (ID {employee_id}).")

        if self.on_saved:
            self.on_saved()

    # -----------------------------------------------------
    # Deactivate handling (edit mode only)
    # -----------------------------------------------------
    def handle_deactivate(self):
        first_name = self.vars["first_name"].get().strip()
        last_name = self.vars["last_name"].get().strip()

        confirmed = messagebox.askyesno(
            "Deactivate Employee",
            f"Deactivate {first_name} {last_name}? "
            f"They will be removed from active lists, but their history "
            f"(leave, reviews, recognition) will be kept.",
        )
        if not confirmed:
            return

        deactivate_employee(self.employee_id)
        messagebox.showinfo("Deactivated", f"{first_name} {last_name} has been deactivated.")

        if self.on_saved:
            self.on_saved()