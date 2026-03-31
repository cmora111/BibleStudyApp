from __future__ import annotations

from pathlib import Path
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class DatasetImportWizard(tk.Toplevel):
    """
    Fully working Tkinter dataset import wizard.
    """

    def __init__(self, parent, dataset_manager, on_complete=None):
        super().__init__(parent)
        self.parent = parent
        self.dataset_manager = dataset_manager
        self.on_complete = on_complete

        self.title("Dataset Import Wizard")
        self.geometry("860x620")
        self.minsize(760, 520)
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.dataset_key_var = tk.StringVar()
        self.file_path_var = tk.StringVar()
        self.copy_into_target_var = tk.BooleanVar(value=True)
        self.validation_state_var = tk.StringVar(value="No file selected")
        self.selected_item = None

        self._build_ui()
        self._populate_dataset_choices()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        header = ttk.Label(
            outer,
            text="Import a local dataset file into the app",
            font=("TkDefaultFont", 12, "bold"),
        )
        header.pack(anchor="w", pady=(0, 8))

        desc = ttk.Label(
            outer,
            text=(
                "Choose a dataset type, select a local file, validate it, "
                "then register it into the app's expected dataset location."
            ),
            wraplength=780,
            justify="left",
        )
        desc.pack(anchor="w", pady=(0, 12))

        form = ttk.LabelFrame(outer, text="1. Choose Dataset")
        form.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(form)
        row1.pack(fill="x", padx=8, pady=8)

        ttk.Label(row1, text="Dataset:").pack(side="left")
        self.dataset_combo = ttk.Combobox(
            row1,
            textvariable=self.dataset_key_var,
            state="readonly",
            width=50,
        )
        self.dataset_combo.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.dataset_combo.bind("<<ComboboxSelected>>", lambda e: self._on_dataset_selected())

        self.dataset_meta = tk.Text(form, height=5, wrap="word")
        self.dataset_meta.pack(fill="x", padx=8, pady=(0, 8))

        source_box = ttk.LabelFrame(outer, text="2. Select Local File")
        source_box.pack(fill="x", pady=(0, 10))

        row2 = ttk.Frame(source_box)
        row2.pack(fill="x", padx=8, pady=8)

        self.file_entry = ttk.Entry(row2, textvariable=self.file_path_var)
        self.file_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(row2, text="Browse...", command=self._browse_file).pack(side="left", padx=(8, 0))
        ttk.Button(row2, text="Validate", command=self.validate_selection).pack(side="left", padx=(8, 0))

        opts = ttk.Frame(source_box)
        opts.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Checkbutton(
            opts,
            text="Copy file into dataset target location",
            variable=self.copy_into_target_var,
        ).pack(anchor="w")
        ttk.Label(
            opts,
            text="Usually leave this enabled. It copies the selected file into the app's expected dataset path.",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        preview_box = ttk.LabelFrame(outer, text="3. Validation + Preview")
        preview_box.pack(fill="both", expand=True, pady=(0, 10))

        status_bar = ttk.Frame(preview_box)
        status_bar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(status_bar, text="Validation Status:").pack(side="left")
        ttk.Label(status_bar, textvariable=self.validation_state_var).pack(side="left", padx=(8, 0))

        self.preview = tk.Text(preview_box, wrap="word")
        self.preview.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Import Dataset", command=self.import_dataset).pack(side="right")
        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="right", padx=(0, 8))

    def _populate_dataset_choices(self):
        labels = []
        self._dataset_lookup = {}
        for item in self.dataset_manager.catalog:
            label = f"{item.label} [{item.category}]"
            labels.append(label)
            self._dataset_lookup[label] = item

        self.dataset_combo["values"] = labels
        if labels:
            self.dataset_combo.current(0)
            self._on_dataset_selected()

    def _on_dataset_selected(self):
        label = self.dataset_combo.get().strip()
        self.selected_item = self._dataset_lookup.get(label)
        self.dataset_meta.delete("1.0", "end")

        if not self.selected_item:
            return

        self.dataset_key_var.set(self.selected_item.key)
        target = self.dataset_manager.resolve_path(self.selected_item.target_path)

        lines = [
            f"Label: {self.selected_item.label}",
            f"Key: {self.selected_item.key}",
            f"Category: {self.selected_item.category}",
            f"Target Path: {target}",
            "",
            f"Description: {self.selected_item.description}",
        ]
        self.dataset_meta.insert("1.0", "\n".join(lines))

    def _browse_file(self):
        try:
            self.lift()
            self.focus_force()
            self.update_idletasks()
            path = filedialog.askopenfilename(
                parent=self,
                title="Select dataset file",
                filetypes=[
                    ("Supported", "*.csv *.txt *.tsv *.pdf *.json *.xml *.zip"),
                    ("CSV files", "*.csv"),
                    ("Text files", "*.txt *.tsv"),
                    ("PDF files", "*.pdf"),
                    ("All files", "*.*"),
                ],
            )
        except Exception as exc:
            messagebox.showerror("Dataset Import Wizard", f"Could not open file picker:\n\n{exc}", parent=self)
            return

        self.lift()
        self.focus_force()

        if path:
            self.file_path_var.set(path)
            self.validation_state_var.set("File selected; not yet validated")
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", f"Selected file:\n{path}\n")
        else:
            self.validation_state_var.set("Browse canceled")

    def validate_selection(self):
        self.preview.delete("1.0", "end")

        if not self.selected_item:
            self.validation_state_var.set("Choose a dataset first")
            return False

        raw = self.file_path_var.get().strip()
        if not raw:
            self.validation_state_var.set("Choose a local file first")
            return False

        path = Path(raw).expanduser()
        if not path.exists():
            self.validation_state_var.set("Selected file does not exist")
            self.preview.insert("1.0", f"Missing file: {path}")
            return False

        size_mb = path.stat().st_size / 1024 / 1024
        suffix = path.suffix.lower()

        lines = [
            f"Selected file: {path}",
            f"Size: {size_mb:.2f} MB",
            f"Suffix: {suffix or '(none)'}",
            "",
        ]

        ok = True

        if suffix in {".csv", ".tsv", ".txt"}:
            text_ok, preview_lines = self._validate_tabular_text(path)
            ok = ok and text_ok
            lines.append("Tabular/Text Validation:")
            lines.extend(preview_lines)
        elif suffix == ".pdf":
            lines.append("PDF Validation:")
            lines.append("- PDF selected. This wizard can register it, but PDF-to-dataset conversion must happen in your importer pipeline.")
            lines.append("- Use this for source preservation, not direct Bible-row import.")
        elif suffix in {".json", ".xml", ".zip"}:
            lines.append("Archive/Structured Validation:")
            lines.append(f"- {suffix} selected. Basic registration is supported.")
            lines.append("- No deep structural validation is performed here.")
        else:
            lines.append("General Validation:")
            lines.append("- Unknown file extension. Registration is still allowed if you know this matches the dataset type.")

        target = self.dataset_manager.resolve_path(self.selected_item.target_path)
        lines.extend(
            [
                "",
                "Dataset target path:",
                f"- {target}",
                f"- Copy into target: {'Yes' if self.copy_into_target_var.get() else 'No'}",
            ]
        )

        self.preview.insert("1.0", "\n".join(lines))
        self.validation_state_var.set("Validation passed" if ok else "Validation has warnings")
        return True

    def _validate_tabular_text(self, path: Path):
        suffix = path.suffix.lower()
        delimiter = ","
        if suffix == ".tsv":
            delimiter = "\t"

        lines = []
        try:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
                sample = f.read(8192)
        except Exception as exc:
            return False, [f"- Could not read file: {exc}"]

        if not sample.strip():
            return False, ["- File appears empty"]

        sample_lines = [line for line in sample.splitlines() if line.strip()]
        lines.append("- Non-empty text file detected")
        lines.append(f"- Sample lines found: {len(sample_lines[:5])}")

        if suffix in {".csv", ".tsv"}:
            try:
                with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    rows = []
                    for idx, row in enumerate(reader):
                        rows.append(row)
                        if idx >= 4:
                            break

                widths = [len(r) for r in rows if r]
                lines.append(f"- Parsed preview rows: {len(rows)}")
                if widths:
                    lines.append(f"- Preview column counts: {widths}")
                if rows:
                    header = rows[0]
                    lines.append(f"- Header preview: {header[:8]}")
                return True, lines
            except Exception as exc:
                lines.append(f"- CSV/TSV parse warning: {exc}")
                return False, lines

        for i, line in enumerate(sample_lines[:5], start=1):
            lines.append(f"- Line {i}: {line[:180]}")
        return True, lines

    def import_dataset(self):
        if not self.validate_selection():
            answer = messagebox.askyesno(
                "Import Dataset",
                "Validation did not fully pass. Do you want to continue anyway?",
                parent=self,
            )
            if not answer:
                return

        if not self.selected_item:
            messagebox.showinfo("Import Dataset", "Choose a dataset first.", parent=self)
            return

        source = self.file_path_var.get().strip()
        if not source:
            messagebox.showinfo("Import Dataset", "Choose a local file first.", parent=self)
            return

        try:
            info = self.dataset_manager.register_local_file(
                self.selected_item.key,
                source,
                copy_into_target=self.copy_into_target_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Import Dataset", f"Could not import dataset:\n\n{exc}", parent=self)
            return

        target = self.dataset_manager.resolve_path(self.selected_item.target_path)
        self.validation_state_var.set("Import complete")
        self.preview.insert(
            "end",
            "\n\nImport complete.\n"
            f"- Registered key: {self.selected_item.key}\n"
            f"- Target path: {target}\n"
            f"- Size bytes: {info.get('size_bytes', 'unknown')}\n"
            f"- SHA256: {info.get('sha256', 'unknown')}\n",
        )

        if callable(self.on_complete):
            try:
                self.on_complete()
            except Exception:
                pass

        messagebox.showinfo(
            "Import Dataset",
            f"Imported '{self.selected_item.label}' successfully.",
            parent=self,
        )
