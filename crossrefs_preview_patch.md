# Cross References Panel: Verse Text Previews Patch

Apply these changes to `app/ui/main_window.py`.

## 1) Add helper methods inside `UltimateBibleApp`

```python
def get_crossref_preview_rows_for_current(self):
    book = self.normalize_current_book()
    chapter = int(self.chapter_var.get())
    verse = int(self.verse_var.get())

    rows = []

    if hasattr(self, "crossref_engine") and self.crossref_engine:
        refs = self.crossref_engine.get_cross_references(
            book,
            chapter,
            verse,
            limit=50,
        )

        for r in refs:
            ref_label = f"{r.target_book.title()} {r.target_chapter}:{r.target_verse}"
            preview_text = self.fetch_verse_text(
                r.target_book,
                r.target_chapter,
                r.target_verse,
                translation=self.translation_var.get().strip().lower(),
            )
            if not preview_text:
                preview_text = self.fetch_verse_text(
                    r.target_book,
                    r.target_chapter,
                    r.target_verse,
                    translation="esv",
                )
            rows.append({
                "ref": ref_label,
                "votes": r.votes,
                "text": preview_text or "(verse text unavailable)",
            })

    if not rows:
        for ref in self.get_crossrefs_for_current():
            parsed = self.parse_reference_label(ref)
            if not parsed:
                rows.append({
                    "ref": ref,
                    "votes": 0,
                    "text": "(preview unavailable)",
                })
                continue

            tgt_book, tgt_chapter, tgt_verse = parsed
            preview_text = self.fetch_verse_text(
                tgt_book,
                tgt_chapter,
                tgt_verse,
                translation=self.translation_var.get().strip().lower(),
            )
            if not preview_text:
                preview_text = self.fetch_verse_text(
                    tgt_book,
                    tgt_chapter,
                    tgt_verse,
                    translation="esv",
                )

            rows.append({
                "ref": f"{tgt_book.title()} {tgt_chapter}:{tgt_verse}",
                "votes": 0,
                "text": preview_text or "(verse text unavailable)",
            })

    return rows


def fetch_verse_text(self, book: str, chapter: int, verse: int, translation: str = "esv"):
    try:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT text
                FROM verses
                WHERE translation=? AND book=? AND chapter=? AND verse=?
                """,
                (translation, book, int(chapter), int(verse)),
            ).fetchone()
        if row:
            return row["text"] if hasattr(row, "keys") else row[0]
    except Exception:
        return None
    return None


def parse_reference_label(self, ref: str):
    ref = (ref or "").strip()
    if not ref or ":" not in ref:
        return None

    try:
        left, verse_s = ref.rsplit(":", 1)
        verse = int(verse_s.strip())
        parts = left.strip().split()
        chapter = int(parts[-1])
        raw_book = " ".join(parts[:-1]).strip()
        book = self.normalize_book_name(raw_book)
        return (book, chapter, verse)
    except Exception:
        return None


def open_crossref_preview_window(self, ref_label: str, verse_text: str):
    top = tk.Toplevel(self.root)
    top.title(ref_label)
    top.geometry("700x240")

    frame = ttk.Frame(top, padding=10)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=ref_label, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")

    text = tk.Text(frame, wrap="word", height=8)
    text.pack(fill="both", expand=True, pady=(8, 0))
    text.insert("1.0", verse_text or "(verse text unavailable)")
    text.configure(state="disabled")
```

## 2) Replace the Cross Refs panel renderer

Use this implementation pattern:

```python
def refresh_crossrefs_panel(self):
    for child in self.crossrefs_container.winfo_children():
        child.destroy()

    rows = self.get_crossref_preview_rows_for_current()

    if not rows:
        ttk.Label(
            self.crossrefs_container,
            text="No cross references found.",
        ).pack(anchor="w", padx=6, pady=6)
        return

    for row in rows:
        outer = ttk.Frame(self.crossrefs_container, padding=(6, 6))
        outer.pack(fill="x", expand=True, anchor="n")

        header = ttk.Frame(outer)
        header.pack(fill="x", expand=True)

        ref_link = tk.Label(
            header,
            text=row["ref"],
            fg="#1a73e8",
            cursor="hand2",
            font=("TkDefaultFont", 10, "underline"),
        )
        ref_link.pack(side="left", anchor="w")

        if row["votes"]:
            ttk.Label(
                header,
                text=f"score {row['votes']}",
            ).pack(side="right", anchor="e")

        ref_link.bind(
            "<Button-1>",
            lambda e, ref=row["ref"], text=row["text"]: self.open_crossref_preview_window(ref, text),
        )

        preview = row["text"]
        if len(preview) > 220:
            preview = preview[:217].rstrip() + "..."

        body = tk.Label(
            outer,
            text=preview,
            justify="left",
            anchor="w",
            wraplength=520,
        )
        body.pack(fill="x", expand=True, anchor="w", pady=(4, 0))
        body.bind(
            "<Button-1>",
            lambda e, ref=row["ref"], text=row["text"]: self.open_crossref_preview_window(ref, text),
        )
        body.configure(cursor="hand2")

        ttk.Separator(self.crossrefs_container).pack(fill="x", padx=6, pady=2)
```

## 3) Refresh after navigation

Wherever you already refresh the verse display after changing book/chapter/verse, also call:

```python
self.refresh_crossrefs_panel()
```

## 4) Optional: navigate + popup on click

```python
def _open_and_navigate(ref_label, verse_text):
    parsed = self.parse_reference_label(ref_label)
    if parsed:
        book, chapter, verse = parsed
        self.set_reference(book, chapter, verse)
    self.open_crossref_preview_window(ref_label, verse_text)
```
