"""
compliance_view.py
Team-wide compliance review screen: overdue + upcoming reviews in one
list. Selecting a review and clicking "Mark Completed" logs it done
and auto-schedules the follow-up review based on the review_type's
frequency.

Usage from main.py:
    from compliance_view import ComplianceViewFrame
    ComplianceViewFrame(self.content, session=self.session)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from compliance_queries import (
    get_overdue_reviews,
    get_upcoming_reviews,
    complete_review,
    waive_review,
)
from review_type_queries import get_all_review_types, set_review_type_active
from review_type_form import ReviewTypeDialog
from review_scheduling import backfill_missing_reviews


class ComplianceViewFrame(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Compliance Reviews", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        ttk.Button(header, text="Manage Review Types", command=self.open_manage_types).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(header, text="Refresh", command=self.refresh).pack(side="right")

        # --- Overdue section ---
        ttk.Label(self, text="Overdue", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(4, 4)
        )
        self.overdue_tree = self._build_tree()
        self.overdue_tree.pack(fill="both", expand=False, pady=(0, 16))

        # --- Upcoming section ---
        ttk.Label(self, text="Upcoming (next 30 days)", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(4, 4)
        )
        self.upcoming_tree = self._build_tree()
        self.upcoming_tree.pack(fill="both", expand=False, pady=(0, 16))

        # --- Action buttons ---
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Mark Selected Completed", command=self.handle_complete).pack(
            side="left"
        )
        ttk.Button(actions, text="Waive Selected", command=self.handle_waive).pack(
            side="left", padx=(8, 0)
        )

        self.status_label = ttk.Label(self, text="", foreground="gray")
        self.status_label.pack(anchor="w", pady=(8, 0))

        self._row_to_review_id = {}
        self.refresh()

    def _build_tree(self):
        columns = ("Employee", "Review Type", "Scheduled Date")
        tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse", height=6)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200, anchor="w")
        return tree

    def refresh(self):
        manager_id = self.session.manager_id
        self._row_to_review_id.clear()

        self.overdue_tree.delete(*self.overdue_tree.get_children())
        overdue = get_overdue_reviews(manager_id)
        if not overdue:
            self.overdue_tree.insert("", "end", values=("No overdue reviews.", "", ""))
        for r in overdue:
            row_id = self.overdue_tree.insert(
                "", "end",
                values=(f"{r['first_name']} {r['last_name']}", r["review_type_name"], r["scheduled_date"]),
            )
            self._row_to_review_id[row_id] = r["review_id"]

        self.upcoming_tree.delete(*self.upcoming_tree.get_children())
        upcoming = get_upcoming_reviews(manager_id)
        if not upcoming:
            self.upcoming_tree.insert("", "end", values=("Nothing in the next 30 days.", "", ""))
        for r in upcoming:
            row_id = self.upcoming_tree.insert(
                "", "end",
                values=(f"{r['first_name']} {r['last_name']}", r["review_type_name"], r["scheduled_date"]),
            )
            self._row_to_review_id[row_id] = r["review_id"]

        self.status_label.config(text="")

    def _get_selected_review_id(self):
        for tree in (self.overdue_tree, self.upcoming_tree):
            selection = tree.selection()
            if selection:
                return self._row_to_review_id.get(selection[0])
        return None

    def handle_complete(self):
        review_id = self._get_selected_review_id()
        if review_id is None:
            messagebox.showwarning("No Selection", "Select a review to mark completed.")
            return

        summary = simpledialog.askstring(
            "Review Summary", "Brief summary/outcome (optional):", parent=self
        )

        complete_review(review_id, conducted_by_manager_id=self.session.manager_id, summary=summary)

        messagebox.showinfo(
            "Completed",
            "Review marked completed. The next occurrence has been auto-scheduled.",
        )
        self.refresh()

    def handle_waive(self):
        review_id = self._get_selected_review_id()
        if review_id is None:
            messagebox.showwarning("No Selection", "Select a review to waive.")
            return

        confirmed = messagebox.askyesno(
            "Waive Review",
            "Waive this review? No follow-up will be auto-scheduled.",
        )
        if not confirmed:
            return

        waive_review(review_id)
        messagebox.showinfo("Waived", "Review has been waived.")
        self.refresh()

    # -----------------------------------------------------
    # Manage Review Types panel
    # -----------------------------------------------------
    def open_manage_types(self):
        panel = tk.Toplevel(self)
        panel.title("Manage Review Types")
        panel.geometry("520x380")
        panel.transient(self)
        panel.grab_set()

        header = ttk.Frame(panel, padding=(16, 16, 16, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Review Types", font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(
            header, text="Add New Type",
            command=lambda: self._open_type_dialog(panel, tree, None),
        ).pack(side="right")

        columns = ("Name", "Frequency", "Active")
        tree = ttk.Treeview(panel, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="w")
        tree.pack(fill="both", expand=True, padx=16, pady=8)

        row_to_type_id = {}

        def refresh_types():
            tree.delete(*tree.get_children())
            row_to_type_id.clear()
            for rt in get_all_review_types(include_inactive=True):
                freq_text = f"Every {rt['frequency']} {rt['frequency_unit']}"
                active_text = "Yes" if rt["is_active"] else "No"
                row_id = tree.insert("", "end", values=(rt["name"], freq_text, active_text))
                row_to_type_id[row_id] = rt["review_type_id"]

        def get_selected_type_id():
            selection = tree.selection()
            if not selection:
                return None
            return row_to_type_id.get(selection[0])

        def handle_edit():
            type_id = get_selected_type_id()
            if type_id is None:
                messagebox.showwarning("No Selection", "Select a review type to edit.", parent=panel)
                return
            self._open_type_dialog(panel, tree, type_id, refresh_callback=refresh_types)

        def handle_toggle_active():
            type_id = get_selected_type_id()
            if type_id is None:
                messagebox.showwarning("No Selection", "Select a review type first.", parent=panel)
                return

            current = get_all_review_types(include_inactive=True)
            current_row = next((r for r in current if r["review_type_id"] == type_id), None)
            if current_row is None:
                return

            new_state = not bool(current_row["is_active"])
            action = "Activate" if new_state else "Deactivate"
            confirmed = messagebox.askyesno(
                f"{action} Review Type",
                f"{action} '{current_row['name']}'? "
                f"This does not affect already-scheduled reviews.",
                parent=panel,
            )
            if not confirmed:
                return

            set_review_type_active(type_id, new_state)
            refresh_types()

        actions = ttk.Frame(panel, padding=(16, 0, 16, 16))
        actions.pack(fill="x")
        ttk.Button(actions, text="Edit Selected", command=handle_edit).pack(side="left")
        ttk.Button(actions, text="Activate/Deactivate Selected", command=handle_toggle_active).pack(
            side="left", padx=(8, 0)
        )

        def handle_backfill():
            confirmed = messagebox.askyesno(
                "Backfill Missing Reviews",
                "This creates an initial scheduled review for any active employee "
                "who doesn't already have one for an active review type. "
                "Employees who already have review history are left untouched. Continue?",
                parent=panel,
            )
            if not confirmed:
                return

            result = backfill_missing_reviews()
            messagebox.showinfo(
                "Backfill Complete",
                f"Created {result['created']} review(s) across "
                f"{result['employees_affected']} employee(s).",
                parent=panel,
            )
            self.refresh()

        ttk.Button(actions, text="Backfill Missing Reviews", command=handle_backfill).pack(
            side="right"
        )

        refresh_types()

    def _open_type_dialog(self, panel_parent, tree, review_type_id, refresh_callback=None):
        def on_saved():
            if refresh_callback:
                refresh_callback()
            self.refresh()  # also refresh the main compliance lists

        ReviewTypeDialog(panel_parent, review_type_id=review_type_id, on_saved=on_saved)