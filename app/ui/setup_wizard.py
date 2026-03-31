from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from app.ui.dataset_import_wizard import DatasetImportWizard
except Exception:
    DatasetImportWizard = None


class SetupWizard(tk.Toplevel):
    """
    First-run / recovery setup wizard for the Ultimate Bible Study App.
    """

    REQUIRED_KEYS = ("timeline_csv", "asv_csv", "kjv_csv")

    def __init__(self, parent, dataset_manager, on_complete=None):
        super().__init__(parent)
        self.parent = parent
        self.dataset_manager = dataset_manager
        self.on_complete = on_complete

        self.title("Setup Wizard")
        self.geometry("900x660")
        self.minsize(780, 560)
        self.transient(parent)
        self.grab_set()

        self.status_var = tk.StringVar(value="Ready")
        self.selected_key_var = tk.StringVar(value="")
        self._rows_by_key = {}

        self._build_ui()
        self.refresh_status()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Ultimate Bible Study App - Setup Wizard",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            outer,
            text=(
                "Use this wizard to check disk space, inspect required datasets, "
                "register missing local files, and verify that the app is ready."
            ),
            wraplength=860,
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        top = ttk.Frame(outer)
        top.pack(fill="both", expand=True)

        left = ttk.LabelFrame(top, text="Dataset Status")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = ttk.LabelFrame(top, text="Details")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        toolbar = ttk.Frame(left)
        toolbar.pack(fill="x", padx=8, pady=8)

        ttk.Button(toolbar, text="Refresh", command=self.refresh_status).pack(side="left")
        ttk.Button(toolbar, text="Check Disk", command=self.show_disk_status).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Open Import Wizard", command=self.open_import_wizard).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Register Local File", command=self.register_selected_local_file).pack(side="left", padx=(6, 0))

        self.tree = ttk.Treeview(
            left,
            columns=("required", "installed", "size_mb", "path"),
            show="headings",
            height=16,
        )
        self.tree.heading("required", text="Required")
        self.tree.heading("installed", text="Installed")
        self.tree.heading("size_mb", text="Size MB")
        self.tree.heading("path", text="Path")
        self.tree.column("required", width=80, anchor="center")
        self.tree.column("installed", width=80, anchor="center")
        self.tree.column("size_mb", width=90, anchor="e")
        self.tree.column("path", width=420, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_selected_details())

        self.details = tk.Text(right, wrap="word")
        self.details.pack(fill="both", expand=True, padx=8, pady=8)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))

        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")
        ttk.Button(bottom, text="Finish", command=self.finish).pack(side="right")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right", padx=(0, 8))

    def refresh_status(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self.dataset_manager.installed_items()
        self._rows_by_key = {row["key"]: row for row in rows}

        missing_required = []
        for row in rows:
            required = "Yes" if row["key"] in self.REQUIRED_KEYS else "No"
            installed = "Yes" if row["exists"] else "No"
            if row["key"] in self.REQUIRED_KEYS and not row["exists"]:
                missing_required.append(row["label"])

            self.tree.insert(
                "",
                "end",
                iid=row["key"],
                values=(required, installed, row["size_mb"], row["path"]),
                text=row["label"],
            )

        if missing_required:
            self.status_var.set("Missing required datasets: " + ", ".join(missing_required))
        else:
            self.status_var.set("All required datasets are present")

        self.details.delete("1.0", "end")
        self.details.insert("1.0", "Setup summary\n\n")
        self.details.insert("end", f"Required dataset keys: {', '.join(self.REQUIRED_KEYS)}\n")
        self.details.insert("end", f"Catalog size: {len(rows)}\n")
        self.details.insert("end", f"Missing required datasets: {len(missing_required)}\n")

    def show_disk_status(self):
        disk = self.dataset_manager.free_disk_space()
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "Disk Status\n\n")
        self.details.insert("end", f"Path: {disk['path']}\n")
        self.details.insert("end", f"Total GB: {disk['total_gb']}\n")
        self.details.insert("end", f"Free GB: {disk['free_gb']}\n")

    def show_selected_details(self):
        selected = self.tree.selection()
        if not selected:
            return

        key = selected[0]
        row = self._rows_by_key.get(key)
        item = self.dataset_manager.get_item(key)

        self.selected_key_var.set(key)
        self.details.delete("1.0", "end")
        self.details.insert("1.0", f"{item.label}\n\n")
        self.details.insert("end", f"Key: {item.key}\n")
        self.details.insert("end", f"Category: {item.category}\n")
        self.details.insert("end", f"Required: {'Yes' if item.key in self.REQUIRED_KEYS else 'No'}\n")
        self.details.insert("end", f"Installed: {'Yes' if row['exists'] else 'No'}\n")
        self.details.insert("end", f"Size MB: {row['size_mb']}\n")
        self.details.insert("end", f"Target Path: {row['path']}\n\n")
        self.details.insert("end", f"{item.description}\n")

        if not row["exists"]:
            self.details.insert("end", "\nSuggested next step: Register a local file or open the import wizard.\n")

    def register_selected_local_file(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Setup Wizard", "Select a dataset row first.", parent=self)
            return

        key = selected[0]
        item = self.dataset_manager.get_item(key)
        local_file = filedialog.askopenfilename(
            title=f"Select local file for {item.label}",
            filetypes=[("All files", "*.*")],
        )
        if not local_file:
            return

        try:
            self.dataset_manager.register_local_file(key, local_file, copy_into_target=True)
        except Exception as exc:
            messagebox.showerror("Setup Wizard", f"Could not register file:\n\n{exc}", parent=self)
            return

        self.refresh_status()
        self.details.insert("end", f"\nRegistered local file for {item.label}.\n")

    def open_import_wizard(self):
        if DatasetImportWizard is None:
            messagebox.showerror(
                "Setup Wizard",
                "DatasetImportWizard could not be imported. Make sure app/ui/dataset_import_wizard.py exists.",
                parent=self,
            )
            return

        def _done():
            self.refresh_status()
            if callable(self.on_complete):
                try:
                    self.on_complete()
                except Exception:
                    pass

        DatasetImportWizard(self, self.dataset_manager, on_complete=_done)

    def finish(self):
        rows = self.dataset_manager.installed_items()
        missing_required = [row["label"] for row in rows if row["key"] in self.REQUIRED_KEYS and not row["exists"]]

        if missing_required:
            answer = messagebox.askyesno(
                "Setup Wizard",
                "Some required datasets are still missing:\n\n"
                + "\n".join(missing_required)
                + "\n\nFinish anyway?",
                parent=self,
            )
            if not answer:
                return

        if callable(self.on_complete):
            try:
                self.on_complete()
            except Exception:
                pass

        self.destroy()
