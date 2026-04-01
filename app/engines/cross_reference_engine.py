from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass(slots=True)
class CrossReferenceHit:
    source_ref: str
    target_ref: str
    target_book_start: str
    target_chapter_start: int
    target_verse_start: int
    target_book_end: str
    target_chapter_end: int
    target_verse_end: int
    target_is_range: bool
    votes: int


class CrossReferenceEngine:
    def __init__(self, db=None, csv_path: str | Path | None = None):
        self.db = db
        self.root_dir = Path.cwd()
        self.csv_path = Path(csv_path) if csv_path else self._discover_csv_path()
        self._index = {}
        self._load()

    def _discover_csv_path(self) -> Path | None:
        candidates = [
            self.root_dir / "output" / "crossrefs" / "openbible_crossrefs.csv",
            self.root_dir / "output" / "crossrefs" / "crossrefs.csv",
            self.root_dir / "output" / "crossrefs" / "ASV.csv",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load(self):
        self._index = {}
        if not self.csv_path or not Path(self.csv_path).exists():
            return

        with Path(self.csv_path).open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    key = (
                        (row.get("source_book") or "").strip().lower(),
                        int(row.get("source_chapter") or 0),
                        int(row.get("source_verse") or 0),
                    )
                    if not key[0] or key[1] <= 0 or key[2] <= 0:
                        continue

                    hit = CrossReferenceHit(
                        source_ref=(row.get("source_ref") or "").strip(),
                        target_ref=(row.get("target_ref") or "").strip(),
                        target_book_start=(row.get("target_book_start") or "").strip().lower(),
                        target_chapter_start=int(row.get("target_chapter_start") or 0),
                        target_verse_start=int(row.get("target_verse_start") or 0),
                        target_book_end=(row.get("target_book_end") or "").strip().lower(),
                        target_chapter_end=int(row.get("target_chapter_end") or 0),
                        target_verse_end=int(row.get("target_verse_end") or 0),
                        target_is_range=bool(int(row.get("target_is_range") or 0)),
                        votes=int(row.get("votes") or 0),
                    )
                    self._index.setdefault(key, []).append(hit)
                except Exception:
                    continue

        for key in self._index:
            self._index[key].sort(key=lambda h: h.votes, reverse=True)

    def reload(self):
        self.csv_path = self._discover_csv_path()
        self._load()

    def get_references(self, book: str, chapter: int, verse: int, limit: int = 50):
        key = ((book or "").strip().lower(), int(chapter), int(verse))
        return self._index.get(key, [])[:limit]

    def get_reference_labels(self, book: str, chapter: int, verse: int, limit: int = 20):
        return [hit.target_ref for hit in self.get_references(book, chapter, verse, limit=limit)]
