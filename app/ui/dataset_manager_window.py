from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from app.core.config import DB_FILE
from app.core.dataset_manager import DatasetManager


class DatasetManagerWindow:
    def __init__(self, root, default_output: str | None = None):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.title("Dataset Manager")
        self.win.geometry("900x620")

        default_dir = default_output or str(Path.home() / "Bible" / "BibleStudyApp" / "ultimate_bible_app_v7" / "output")
        self.output_var = tk.StringVar(value=default_dir)
        self.import_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")

        self.manager = None
        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self.win)
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="Output folder").grid(row=0, column=0, sticky="w")
        tk.Entry(top, textvariable=self.output_var, width=90).grid(row=0, column=1, sticky="ew", padx=8)
        top.columnconfigure(1, weight=1)

        opts = tk.Frame(self.win)
        opts.pack(fill="x", padx=10)

        tk.Checkbutton(
            opts,
            text="Import KJV / WEB / ASV into SQLite after download",
            variable=self.import_var,
        ).pack(anchor="w")

        summary = tk.LabelFrame(self.win, text="What this downloads")
        summary.pack(fill="x", padx=10, pady=10)

        items = [
            "WEB, KJV, ASV",
            "Greek NT",
            "Hebrew OT",
            "Strong's lexicons / STEP Bible research tables",
            "Cross-reference / geography related datasets",
            "Resume partial downloads",
            "Verify disk space before downloading",
        ]
        for item in items:
            tk.Label(summary, text=f"• {item}", anchor="w").pack(fill="x", padx=10, pady=1)

        btns = tk.Frame(self.win)
        btns.pack(fill="x", padx=10, pady=10)

        tk.Button(btns, text="Start", command=self.start).pack(side="left")
        tk.Button(btns, text="Cancel", command=self.cancel).pack(side="left", padx=6)

        tk.Label(btns, textvariable=self.status_var).pack(side="left", padx=12)

        self.log = tk.Text(self.win, wrap="word")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def append_log(self, message: str):
        def _append():
            self.log.insert("end", message + "\n")
            self.log.see("end")
        self.win.after(0, _append)

    def set_status(self, message: str):
        self.win.after(0, lambda: self.status_var.set(message))

    def start(self):
        output_dir = self.output_var.get().strip()
        if not output_dir:
            messagebox.showerror("Dataset Manager", "Please provide an output folder.")
            return

        self.log.delete("1.0", "end")
        self.set_status("Running...")

        self.manager = DatasetManager(output_dir, db_path=DB_FILE)
        self.manager.set_callbacks(log_callback=self.append_log, progress_callback=self.set_status)

        def done(error):
            if error is None:
                self.set_status("Completed")
                self.append_log("Finished successfully.")
            else:
                self.set_status("Failed")
                self.append_log(f"ERROR: {error}")
                self.win.after(0, lambda: messagebox.showerror("Dataset Manager", str(error)))

        self.manager.run_in_thread(import_into_db=self.import_var.get(), on_done=done)

    def cancel(self):
        if self.manager is not None:
            self.manager.cancel_requested = True
            self.append_log("Cancellation requested...")
            self.set_status("Cancelling...")
