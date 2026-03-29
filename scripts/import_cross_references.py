#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import DB_FILE
from app.core.book_normalizer import normalize_book_name

REF_RE = re.compile(r"^\s*([1-3]?\s?[A-Za-z .]+)\s+(\d+):(\d+)\s*$")


def parse_ref(ref_text: str):
    m = REF_RE.match(ref_text.strip())
    if not m:
        raise ValueError(f"Bad reference: {ref_text}")
    raw_book, chapter_s, verse_s = m.groups()
    book = normalize_book_name(raw_book.strip())
    return book, int(chapter_s), int(verse_s)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cross_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_book TEXT NOT NULL,
            source_chapter INTEGER NOT NULL,
            source_verse INTEGER NOT NULL,
            target_book TEXT NOT NULL,
            target_chapter INTEGER NOT NULL,
            target_verse INTEGER NOT NULL,
            votes INTEGER DEFAULT 0,
            source_label TEXT DEFAULT '',
            target_label TEXT DEFAULT '',
            note TEXT DEFAULT '',
            dataset TEXT DEFAULT 'custom',
            UNIQUE (
                source_book, source_chapter, source_verse,
                target_book, target_chapter, target_verse, dataset
            )
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cross_refs_source
        ON cross_references(source_book, source_chapter, source_verse, votes DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cross_refs_target
        ON cross_references(target_book, target_chapter, target_verse)
    """)
    conn.commit()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/import_cross_references.py crossrefs.csv [--replace-dataset tsk]")
        return 1

    csv_path = Path(sys.argv[1]).expanduser().resolve()
    if not csv_path.exists():
        print(f"Missing file: {csv_path}")
        return 1

    dataset = "custom"
    replace_dataset = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--replace-dataset":
        replace_dataset = sys.argv[3].strip()
        dataset = replace_dataset

    conn = sqlite3.connect(DB_FILE)
    ensure_schema(conn)

    if replace_dataset:
        conn.execute("DELETE FROM cross_references WHERE dataset=?", (replace_dataset,))
        conn.commit()

    inserted = 0
    skipped = 0
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            try:
                source_book, source_chapter, source_verse = parse_ref(row["source_ref"])
                target_book, target_chapter, target_verse = parse_ref(row["target_ref"])
                votes = int((row.get("votes") or "0").strip() or 0)
                dataset_name = (row.get("dataset") or dataset or "custom").strip()
                rows.append((
                    source_book, source_chapter, source_verse,
                    target_book, target_chapter, target_verse,
                    votes,
                    row.get("source_ref", "").strip(),
                    row.get("target_ref", "").strip(),
                    row.get("note", "").strip(),
                    dataset_name,
                ))
            except Exception:
                skipped += 1

        conn.executemany("""
            INSERT OR REPLACE INTO cross_references (
                source_book, source_chapter, source_verse,
                target_book, target_chapter, target_verse,
                votes, source_label, target_label, note, dataset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        inserted = len(rows)

    conn.close()
    print(f"Imported {inserted} cross references into {DB_FILE}")
    print(f"Skipped {skipped} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
