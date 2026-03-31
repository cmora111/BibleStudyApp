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
    Patched Tkinter dataset import wizard.

    Improvements:
    - selected dataset/target path shown clearly at top
    - import button made more visible
    - cross-reference TXT/TSV can be converted directly to CSV inside the wizard
    - status/preview updated after browse and conversion
    """

    def __init__(self, parent, dataset_manager, on_complete=None):
        super().__init__(parent)
        self.parent = parent
        self.dataset_manager = dataset_manager
        self.on_complete = on_complete

        self.title("Dataset Import Wizard")
        self.geometry("900x680")
        self.minsize(780, 560)
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

    def _build_ui(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Import a local dataset file into the app",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            outer,
            text=(
                "Choose the correct dataset type first. Then browse for a local file, "
                "validate it, and import it into the target dataset location."
            ),
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        summary = ttk.LabelFrame(outer, text="Selected Dataset")
        summary.pack(fill="x", pady=(0, 10))
        ttk.Label(summary, textvariable=self.dataset_label_var, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(summary, text="Target path:").pack(anchor="w", padx=8)
        ttk.Label(summary, textvariable=self.target_path_var, wraplength=820, justify="left").pack(anchor="w", padx=20, pady=(0, 8))

        form = ttk.LabelFrame(outer, text="1. Choose Dataset")
        form.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(form)
        row1.pack(fill="x", padx=8, pady=8)

        ttk.Label(row1, text="Dataset:").pack(side="left")
        self.dataset_combo = ttk.Combobox(
            row1,
            textvariable=self.dataset_key_var,
            state="readonly",
            width=54,
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
        ttk.Button(row2, text="Convert Crossrefs TXT -> CSV", command=self.convert_crossrefs_txt_to_csv).pack(side="left", padx=(8, 0))

        opts = ttk.Frame(source_box)
        opts.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Checkbutton(
            opts,
            text="Copy file into dataset target location",
            variable=self.copy_into_target_var,
        ).pack(anchor="w")
        ttk.Label(
            opts,
            text=(
                "Usually leave this enabled. For cross references, choose the Cross References dataset first, "
                "then convert the TXT/TSV file to a CSV and import that CSV."
            ),
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        preview_box = ttk.LabelFrame(outer, text="3. Validation + Preview")
        preview_box.pack(fill="both", expand=True, pady=(0, 10))

        status_bar = ttk.Frame(preview_box)
        status_bar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(status_bar, text="Validation Status:").pack(side="left")
        ttk.Label(status_bar, textvariable=self.validation_state_var).pack(side="left", padx=(8, 0))

        self.preview = tk.Text(preview_box, wrap="word", height=16)
        self.preview.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="right", padx=(0, 8))
        self.import_button = ttk.Button(buttons, text="IMPORT DATASET", command=self.import_dataset)
        self.import_button.pack(side="right", padx=(0, 8))

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
