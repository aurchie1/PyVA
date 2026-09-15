"""
employee_list.py
Roster view: shows all active employees under the logged-in manager
in a table. Click a row (or select + click Edit) to open that
employee in the edit form.

Usage from main.py:
    from employee_list import EmployeeListFrame
    EmployeeListFrame(
        self.content,
        session=self.session,
        on_add=self.show_add_employee,
        on_edit=self.show_edit_employee,
    )
"""

import tkinter as tk
from tkinter import ttk

from create_user import get_all_employees


class EmployeeListFrame(ttk.Frame):
    """
    Args:
        parent: the Tkinter container to place this frame in
        session: the current Session (used to scope the roster to this manager)
        on_add: callback invoked when "Add Employee" is clicked
        on_edit: callback invoked with employee_id when a row is double-clicked
                 or "Edit Selected" is clicked
    """

    def __init__(self, parent, session, on_add=None, on_edit=None):
        super().__init__(parent)
        self.session = session
        self.on_add = on_add
        self.on_edit = on_edit

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(header, text="Employees", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Add Employee", command=self._handle_add).pack(side="right")
        ttk.Button(header, text="Edit Selected", command=self._handle_edit_selected).pack(
            side="right", padx=(0, 8)
        )

        columns = ("Name", "Preferred Name","Position", "Status", "Hire Date")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=180, anchor="w")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", self._handle_row_double_click)

        # Maps Treeview item id -> employee_id, since Treeview items
        # need their own id space separate from the database id.
        self._row_to_employee_id = {}

        self.refresh()

    def refresh(self):
        """Reloads the roster from the database. Call after add/edit/deactivate."""
        self.tree.delete(*self.tree.get_children())
        self._row_to_employee_id.clear()

        employees = get_all_employees(manager_id=self.session.manager_id)

        if not employees:
            self.tree.insert("", "end", values=("No employees yet.", "", "", "", ""))
            return

        for emp in employees:
            row_id = self.tree.insert(
                "", "end",
                values=(
                    f"{emp['first_name']} {emp['last_name']}",
                    emp['preferred_name'] or "",
                    emp["position_title"] or "",
                    emp["employment_status"],
                    emp["hire_date"] or "",
                ),
            )
            self._row_to_employee_id[row_id] = emp["employee_id"]

    def _handle_add(self):
        if self.on_add:
            self.on_add()

    def _get_selected_employee_id(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return self._row_to_employee_id.get(selection[0])

    def _handle_edit_selected(self):
        employee_id = self._get_selected_employee_id()
        if employee_id is None:
            return
        if self.on_edit:
            self.on_edit(employee_id)

    def _handle_row_double_click(self, event):
        employee_id = self._get_selected_employee_id()
        if employee_id is None:
            return
        if self.on_edit:
            self.on_edit(employee_id)
