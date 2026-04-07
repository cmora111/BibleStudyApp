from __future__ import annotations

from pathlib import Path
import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


BOOK_MAP = {
    "Gen": "genesis", "Exod": "exodus", "Lev": "leviticus", "Num": "numbers", "Deut": "deuteronomy",
    "Josh": "joshua", "Judg": "judges", "Ruth": "ruth", "1Sam": "1samuel", "2Sam": "2samuel",
    "1Kgs": "1kings", "2Kgs": "2kings", "1Chr": "1chronicles", "2Chr": "2chronicles", "Ezra": "ezra",
    "Neh": "nehemiah", "Esth": "esther", "Job": "job", "Ps": "psalms", "Prov": "proverbs",
    "Eccl": "ecclesiastes", "Song": "songofsolomon", "Isa": "isaiah", "Jer": "jeremiah",
    "Lam": "lamentations", "Ezek": "ezekiel", "Dan": "daniel", "Hos": "hosea", "Joel": "joel",
    "Amos": "amos", "Obad": "obadiah", "Jonah": "jonah", "Mic": "micah", "Nah": "nahum",
    "Hab": "habakkuk", "Zeph": "zephaniah", "Hag": "haggai", "Zech": "zechariah", "Mal": "malachi",
    "Matt": "matthew", "Mark": "mark", "Luke": "luke", "John": "john", "Acts": "acts",
    "Rom": "romans", "1Cor": "1corinthians", "2Cor": "2corinthians", "Gal": "galatians",
    "Eph": "ephesians", "Phil": "philippians", "Col": "colossians", "1Thess": "1thessalonians",
    "2Thess": "2thessalonians", "1Tim": "1timothy", "2Tim": "2timothy", "Titus": "titus",
    "Phlm": "philemon", "Heb": "hebrews", "Jas": "james", "1Pet": "1peter", "2Pet": "2peter",
    "1John": "1john", "2John": "2john", "3John": "3john", "Jude": "jude", "Rev": "revelation",
}
REF_RE = re.compile(r'^(?P<book>[1-3]?[A-Za-z]+)\.(?P<chapter>\d+)\.(?P<verse>\d+)$')


class DatasetImportWizard(tk.Toplevel):
    """
    Patched Tkinter dataset import wizard with an always-visible import footer.
    """

    def __init__(self, parent, dataset_manager, on_complete=None):
        super().__init__(parent)
        self.parent = parent
        self.dataset_manager = dataset_manager
        self.on_complete = on_complete

        self.title("Dataset Import Wizard")
        self.geometry("920x700")
        self.minsize(820, 620)
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        self.dataset_key_var = tk.StringVar()
        self.dataset_label_var = tk.StringVar(value="No dataset selected")
        self.target_path_var = tk.StringVar(value="No target path selected")
        self.file_path_var = tk.StringVar()
        self.copy_into_target_var = tk.BooleanVar(value=True)
        self.validation_state_var = tk.StringVar(value="No file selected")
        self.selected_item = None

        self._build_ui()
        self._populate_dataset_choices()
        self._sync_import_button_state()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        outer = ttk.Frame(self, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Import a local dataset file into the app",
            font=("TkDefaultFont", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        ttk.Label(
            header,
            text=(
                "Choose the correct dataset type first. Then browse for a local file, "
                "validate it, and import it into the target dataset location."
            ),
            wraplength=840,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        main = ttk.Frame(outer)
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(3, weight=1)
        main.grid_columnconfigure(0, weight=1)

        summary = ttk.LabelFrame(main, text="Selected Dataset")
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        summary.grid_columnconfigure(0, weight=1)

        ttk.Label(
            summary,
            textvariable=self.dataset_label_var,
            font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))

        ttk.Label(summary, text="Target path:").grid(row=1, column=0, sticky="w", padx=8)
        ttk.Label(
            summary,
            textvariable=self.target_path_var,
            wraplength=820,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 8))

        form = ttk.LabelFrame(main, text="1. Choose Dataset")
        form.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        form.grid_columnconfigure(0, weight=1)

        row1 = ttk.Frame(form)
        row1.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        row1.grid_columnconfigure(1, weight=1)

        ttk.Label(row1, text="Dataset:").grid(row=0, column=0, sticky="w")
        self.dataset_combo = ttk.Combobox(
            row1,
            textvariable=self.dataset_key_var,
            state="readonly",
            width=54,
        )
        self.dataset_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.dataset_combo.bind("<<ComboboxSelected>>", lambda e: self._on_dataset_selected())

        self.dataset_meta = tk.Text(form, height=5, wrap="word")
        self.dataset_meta.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        source_box = ttk.LabelFrame(main, text="2. Select Local File")
        source_box.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        source_box.grid_columnconfigure(0, weight=1)

        row2 = ttk.Frame(source_box)
        row2.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        row2.grid_columnconfigure(0, weight=1)

        self.file_entry = ttk.Entry(row2, textvariable=self.file_path_var)
        self.file_entry.grid(row=0, column=0, sticky="ew")

        ttk.Button(row2, text="Browse...", command=self._browse_file).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(row2, text="Validate", command=self.validate_selection).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(row2, text="Convert Crossrefs TXT -> CSV", command=self.convert_crossrefs_txt_to_csv).grid(row=0, column=3, padx=(8, 0))

        opts = ttk.Frame(source_box)
        opts.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        opts.grid_columnconfigure(0, weight=1)

        ttk.Checkbutton(
            opts,
            text="Copy file into dataset target location",
            variable=self.copy_into_target_var,
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            opts,
            text=(
                "Usually leave this enabled. For cross references, choose the Cross References dataset first, "
                "then convert the TXT/TSV file to a CSV and import that CSV."
            ),
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        preview_box = ttk.LabelFrame(main, text="3. Validation + Preview")
        preview_box.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        preview_box.grid_rowconfigure(1, weight=1)
        preview_box.grid_columnconfigure(0, weight=1)

        status_bar = ttk.Frame(preview_box)
        status_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ttk.Label(status_bar, text="Validation Status:").pack(side="left")
        ttk.Label(status_bar, textvariable=self.validation_state_var).pack(side="left", padx=(8, 0))

        preview_wrap = ttk.Frame(preview_box)
        preview_wrap.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        preview_wrap.grid_rowconfigure(0, weight=1)
        preview_wrap.grid_columnconfigure(0, weight=1)

        self.preview = tk.Text(preview_wrap, wrap="word", height=16)
        self.preview.grid(row=0, column=0, sticky="nsew")

        preview_scroll = ttk.Scrollbar(preview_wrap, orient="vertical", command=self.preview.yview)
        preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set)

        footer = ttk.Frame(outer, padding=(0, 6, 0, 0))
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        left_footer = ttk.Frame(footer)
        left_footer.grid(row=0, column=0, sticky="w")
        ttk.Label(left_footer, text="Ready to import when dataset and file are selected.").pack(side="left")

        right_footer = ttk.Frame(footer)
        right_footer.grid(row=0, column=1, sticky="e")

        ttk.Button(right_footer, text="Close", command=self.destroy).pack(side="right", padx=(8, 0))
        self.import_button = ttk.Button(
            right_footer,
            text="IMPORT DATASET",
            command=self.import_dataset
        )
        self.import_button.pack(side="right")

    def _sync_import_button_state(self):
        state = "normal" if (self.selected_item and self.file_path_var.get().strip()) else "disabled"
        try:
            self.import_button.configure(state=state)
        except Exception:
            pass

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
            self.dataset_label_var.set("No dataset selected")
            self.target_path_var.set("No target path selected")
            self._sync_import_button_state()
            return

        self.dataset_key_var.set(self.selected_item.key)
        target = self.dataset_manager.resolve_path(self.selected_item.target_path)
        self.dataset_label_var.set(f"{self.selected_item.label} [{self.selected_item.category}]")
        self.target_path_var.set(str(target))

        lines = [
            f"Label: {self.selected_item.label}",
            f"Key: {self.selected_item.key}",
            f"Category: {self.selected_item.category}",
            f"Target Path: {target}",
            "",
            f"Description: {self.selected_item.description}",
        ]
        self.dataset_meta.insert("1.0", "\n".join(lines))
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", f"Selected dataset:\n- {self.dataset_label_var.get()}\n- Target path: {target}\n")
        self._sync_import_button_state()

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
            self.preview.insert("1.0", f"Selected dataset:\n- {self.dataset_label_var.get()}\n- Target path: {self.target_path_var.get()}\n\nSelected file:\n{path}\n")
        else:
            self.validation_state_var.set("Browse canceled")

        self._sync_import_button_state()

    def validate_selection(self):
        self.preview.delete("1.0", "end")

        if not self.selected_item:
            self.validation_state_var.set("Choose a dataset first")
            self._sync_import_button_state()
            return False

        raw = self.file_path_var.get().strip()
        if not raw:
            self.validation_state_var.set("Choose a local file first")
            self._sync_import_button_state()
            return False

        path = Path(raw).expanduser()
        if not path.exists():
            self.validation_state_var.set("Selected file does not exist")
            self.preview.insert("1.0", f"Missing file: {path}")
            self._sync_import_button_state()
            return False

        size_mb = path.stat().st_size / 1024 / 1024
        suffix = path.suffix.lower()

        lines = [
            f"Selected dataset: {self.dataset_label_var.get()}",
            f"Target path: {self.target_path_var.get()}",
            "",
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
            lines.append("- Use this for source preservation, not direct row import.")
        elif suffix in {".json", ".xml", ".zip"}:
            lines.append("Archive/Structured Validation:")
            lines.append(f"- {suffix} selected. Basic registration is supported.")
            lines.append("- No deep structural validation is performed here.")
        else:
            lines.append("General Validation:")
            lines.append("- Unknown file extension. Registration is still allowed if you know this matches the dataset type.")

        lines.extend(
            [
                "",
                "Dataset target path:",
                f"- {self.target_path_var.get()}",
                f"- Copy into target: {'Yes' if self.copy_into_target_var.get() else 'No'}",
            ]
        )

        self.preview.insert("1.0", "\n".join(lines))
        self.validation_state_var.set("Validation passed" if ok else "Validation has warnings")
        self._sync_import_button_state()
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

    def _parse_ref(self, ref: str):
        m = REF_RE.match((ref or "").strip())
        if not m:
            raise ValueError(f"Unsupported verse format: {ref}")
        book_token = m.group("book")
        chapter = int(m.group("chapter"))
        verse = int(m.group("verse"))
        book = BOOK_MAP.get(book_token)
        if not book:
            raise ValueError(f"Unknown book token: {book_token}")
        return book, chapter, verse

    def _parse_ref_or_range(self, value: str):
        value = (value or "").strip()
        if "-" in value:
            left, right = value.split("-", 1)
            sb, sc, sv = self._parse_ref(left)
            eb, ec, ev = self._parse_ref(right)
            return {
                "book_start": sb, "chapter_start": sc, "verse_start": sv,
                "book_end": eb, "chapter_end": ec, "verse_end": ev,
                "is_range": True,
            }
        b, c, v = self._parse_ref(value)
        return {
            "book_start": b, "chapter_start": c, "verse_start": v,
            "book_end": b, "chapter_end": c, "verse_end": v,
            "is_range": False,
        }

    def convert_crossrefs_txt_to_csv(self):
        if not self.selected_item:
            messagebox.showinfo("Crossrefs Conversion", "Choose a dataset first.", parent=self)
            return

        if "cross" not in self.selected_item.label.lower():
            messagebox.showwarning(
                "Crossrefs Conversion",
                "You currently have a non-crossrefs dataset selected.\n\n"
                "Select the Cross References dataset first so the target path is correct.",
                parent=self,
            )
            return

        raw = self.file_path_var.get().strip()
        if not raw:
            messagebox.showinfo("Crossrefs Conversion", "Browse for the cross references TXT/TSV file first.", parent=self)
            return

        input_path = Path(raw).expanduser()
        if not input_path.exists():
            messagebox.showerror("Crossrefs Conversion", f"Input file not found:\n\n{input_path}", parent=self)
            return

        output_default = self.dataset_manager.resolve_path(self.selected_item.target_path)
        output_path_str = filedialog.asksaveasfilename(
            parent=self,
            title="Save converted crossrefs CSV",
            initialfile=output_default.name,
            initialdir=str(output_default.parent),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not output_path_str:
            return

        output_path = Path(output_path_str).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        converted = 0
        skipped = 0
        try:
            with input_path.open("r", encoding="utf-8", errors="replace", newline="") as src, \
                 output_path.open("w", encoding="utf-8", newline="") as dst:

                reader = csv.DictReader(src, delimiter="\t")
                fieldnames = [
                    "source_ref",
                    "source_book",
                    "source_chapter",
                    "source_verse",
                    "target_ref",
                    "target_book_start",
                    "target_chapter_start",
                    "target_verse_start",
                    "target_book_end",
                    "target_chapter_end",
                    "target_verse_end",
                    "target_is_range",
                    "votes",
                ]
                writer = csv.DictWriter(dst, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    try:
                        from_ref = (row.get("From Verse") or "").strip()
                        to_ref = (row.get("To Verse") or "").strip()
                        votes_raw = (row.get("Votes") or "0").strip()

                        source_book, source_chapter, source_verse = self._parse_ref(from_ref)
                        target = self._parse_ref_or_range(to_ref)

                        writer.writerow(
                            {
                                "source_ref": from_ref,
                                "source_book": source_book,
                                "source_chapter": source_chapter,
                                "source_verse": source_verse,
                                "target_ref": to_ref,
                                "target_book_start": target["book_start"],
                                "target_chapter_start": target["chapter_start"],
                                "target_verse_start": target["verse_start"],
                                "target_book_end": target["book_end"],
                                "target_chapter_end": target["chapter_end"],
                                "target_verse_end": target["verse_end"],
                                "target_is_range": int(target["is_range"]),
                                "votes": int(votes_raw),
                            }
                        )
                        converted += 1
                    except Exception:
                        skipped += 1
        except Exception as exc:
            messagebox.showerror("Crossrefs Conversion", f"Could not convert crossrefs file:\n\n{exc}", parent=self)
            return

        self.file_path_var.set(str(output_path))
        self.validation_state_var.set("Crossrefs converted to CSV")
        self.preview.delete("1.0", "end")
        self.preview.insert(
            "1.0",
            f"Crossrefs conversion complete.\n\n"
            f"Selected dataset: {self.dataset_label_var.get()}\n"
            f"Target path: {self.target_path_var.get()}\n\n"
            f"Input: {input_path}\n"
            f"Output CSV: {output_path}\n"
            f"Converted rows: {converted}\n"
            f"Skipped rows: {skipped}\n\n"
            f"You can now click IMPORT DATASET to register this CSV into the dataset target path.",
        )
        self._sync_import_button_state()

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
