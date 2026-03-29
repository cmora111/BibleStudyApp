#!/usr/bin/env python3
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import DB_FILE


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verse_token_tags (
            translation TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            token_index INTEGER NOT NULL,
            token_text TEXT NOT NULL,
            strongs_id TEXT,
            lemma TEXT DEFAULT '',
            gloss TEXT DEFAULT '',
            PRIMARY KEY (translation, book, chapter, verse, token_index)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_verse_token_tags_lookup
        ON verse_token_tags(translation, book, chapter, verse)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_verse_token_tags_strongs
        ON verse_token_tags(strongs_id)
    """)
    conn.commit()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/import_verse_token_tags.py /path/to/tags.csv [--replace-translation esv]")
        return 1

    csv_path = Path(sys.argv[1]).expanduser().resolve()
    if not csv_path.exists():
        print(f"Missing file: {csv_path}")
        return 1

    replace_translation = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--replace-translation":
        replace_translation = sys.argv[3].strip().lower()

    conn = sqlite3.connect(DB_FILE)
    ensure_schema(conn)

    if replace_translation:
        conn.execute("DELETE FROM verse_token_tags WHERE translation=?", (replace_translation,))
        conn.commit()

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append((
                row["translation"].strip().lower(),
                row["book"].strip().lower(),
                int(row["chapter"]),
                int(row["verse"]),
                int(row["token_index"]),
                row["token_text"].strip(),
                row.get("strongs_id", "").strip().upper() or None,
                row.get("lemma", "").strip(),
                row.get("gloss", "").strip(),
            ))
        conn.executemany("""
            INSERT OR REPLACE INTO verse_token_tags
            (translation, book, chapter, verse, token_index, token_text, strongs_id, lemma, gloss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        count = len(rows)

    conn.close()
    print(f"Imported {count} verse token tags into {DB_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
