from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app.core.setup_tasks import (
    build_starter_bundle,
    load_demo_scholar_tokens,
    run_full_setup,
    verify_core_verses,
)


class SetupWizardWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, project_dir: str | Path):
        super().__init__(parent)
        self.title("Ultimate Bible App Setup Wizard")
        self.geometry("760x560")
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.status_var = tk.StringVar(value=f"Project: {self.project_dir}")
        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(top, text="Setup Wizard", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        ttk.Label(top, text="Run setup and verification tasks without leaving the app.").pack(anchor="w", pady=(0, 10))

        actions = ttk.Frame(top)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Load Demo Scholar Tokens", command=self.on_load_demo).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Build Starter Strong's Bundle", command=self.on_build_bundle).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Verify Core Verses", command=self.on_verify).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Run Full Setup", command=self.on_full_setup).pack(side="left")

        self.output = tk.Text(top, wrap="word")
        self.output.pack(fill="both", expand=True)

        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", padx=12, pady=(0, 10))

    def _append(self, lines: list[str]) -> None:
        for line in lines:
            self.output.insert("end", f"{line}\n")
        self.output.insert("end", "\n")
        self.output.see("end")

    def on_load_demo(self) -> None:
        report = load_demo_scholar_tokens(self.project_dir)
        self._append(report.messages)
        self.status_var.set("Demo scholar token task finished.")
        if not report.ok:
            messagebox.showwarning("Setup Wizard", "Demo scholar token load finished with warnings.")

    def on_build_bundle(self) -> None:
        report = build_starter_bundle(self.project_dir)
        self._append(report.messages)
        self.status_var.set("Starter Strong's bundle task finished.")
        if not report.ok:
            messagebox.showwarning("Setup Wizard", "Starter bundle build finished with warnings.")

    def on_verify(self) -> None:
        messages = verify_core_verses()
        self._append(messages)
        self.status_var.set("Verification finished.")

    def on_full_setup(self) -> None:
        report = run_full_setup(self.project_dir)
        self._append(report.messages)
        self.status_var.set("Full setup finished.")
        if report.ok:
            messagebox.showinfo("Setup Wizard", "Full setup completed.")
        else:
            messagebox.showwarning("Setup Wizard", "Full setup completed with warnings.")
