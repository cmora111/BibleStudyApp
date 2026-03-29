# Ultimate Bible App v8.1

Version 8.1 is a focused UI reliability update.

## What v8.1 fixes
- reader lookup failures caused by book spelling mismatches
- abbreviations like `gal`, `rom`, `rev`
- common misspellings like `galations`
- more reliable chapter lookup and assistant reference opening

## Files included
- `app/core/book_normalizer.py`
- `docs/INSTALL_V8_1.md`
- `docs/USER_GUIDE_V8_1.md`
- `docs/RELEASE_NOTES_V8_1.md`

## Install
Copy the helper into your project:

```bash
cp app/core/book_normalizer.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8/app/core/
```

## Patch `app/ui/main_window.py`

Add:

```python
from app.core.book_normalizer import normalize_book_name
```

Replace your `current_verse()` method with:

```python
def current_verse(self):
    translation = self.translation_var.get().strip().lower()
    raw_book = self.book_var.get().strip()
    known_books = []
    if hasattr(self.db, "books"):
        try:
            known_books = list(self.db.books(translation))
        except Exception:
            known_books = []
    book = normalize_book_name(raw_book, known_books=known_books)
    self.book_var.set(book)
    return self.db.get_verse(
        translation,
        book,
        int(self.chapter_var.get()),
        int(self.verse_var.get()),
    )
```

Update `open_reference_from_string()` so it uses:

```python
book = normalize_book_name(raw_book)
```

Optional `read_current_chapter()` upgrade:

```python
def read_current_chapter(self):
    translation = self.translation_var.get().strip().lower()
    raw_book = self.book_var.get().strip()
    known_books = []
    if hasattr(self.db, "books"):
        try:
            known_books = list(self.db.books(translation))
        except Exception:
            known_books = []
    book = normalize_book_name(raw_book, known_books=known_books)
    self.book_var.set(book)
    chapter = int(self.chapter_var.get())
    self.open_chapter(book, chapter)
```
