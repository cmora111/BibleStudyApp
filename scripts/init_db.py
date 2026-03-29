#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import ROOT_DIR, DATA_DIR, EXPORT_DIR, CACHE_DIR, DB_FILE
from app.core.bible_db import BibleDB


def ensure_dirs() -> None:
    for p in (ROOT_DIR, DATA_DIR, EXPORT_DIR, CACHE_DIR):
        p.mkdir(parents=True, exist_ok=True)


def ensure_indexes(conn: sqlite3.Connection) -> list[str]:
    msgs: list[str] = []
    table_names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    if "verses" in table_names:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verses_lookup "
            "ON verses(translation, book, chapter, verse)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verses_book_chapter "
            "ON verses(translation, book, chapter)"
        )
        msgs.append("Indexed verses")

    if "strongs" in table_names:
        try:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_strongs_lookup "
                "ON strongs(strongs_id)"
            )
            msgs.append("Indexed strongs")
        except sqlite3.OperationalError:
            pass

    if "scholar_alignment_tokens" in table_names:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scholar_alignment_lookup "
            "ON scholar_alignment_tokens(translation, book, chapter, verse)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scholar_alignment_strongs "
            "ON scholar_alignment_tokens(strongs_id)"
        )
        msgs.append("Indexed scholar_alignment_tokens")

    if "verse_token_tags" in table_names:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verse_token_tags_lookup "
            "ON verse_token_tags(translation, book, chapter, verse)"
        )
        msgs.append("Indexed verse_token_tags")

    conn.commit()
    return msgs


def print_summary(conn: sqlite3.Connection) -> None:
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    print(f"DB file: {DB_FILE}")
    print(f"Tables: {', '.join(tables) if tables else '(none)'}")

    if "verses" in tables:
        print(f"Verse rows: {conn.execute('SELECT COUNT(*) FROM verses').fetchone()[0]}")

    if "strongs" in tables:
        try:
            print(f"Strongs rows: {conn.execute('SELECT COUNT(*) FROM strongs').fetchone()[0]}")
        except sqlite3.OperationalError:
            pass

    if "scholar_alignment_tokens" in tables:
        print(
            f"Scholar token rows: "
            f"{conn.execute('SELECT COUNT(*) FROM scholar_alignment_tokens').fetchone()[0]}"
        )


def main() -> int:
    ensure_dirs()

    # In your project, constructing BibleDB initializes the schema.
    BibleDB()

    conn = sqlite3.connect(DB_FILE)

    print("Database initialized")
    print("- Used app.core.bible_db.BibleDB()")

    for msg in ensure_indexes(conn):
        print(f"- {msg}")

    print_summary(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
