#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DEFAULT_TARGET_DB = Path.home() / "UltimateBibleApp" / "data" / "bible.db"

BOOK_ALIASES = {
    "gen": "genesis", "ge": "genesis", "gn": "genesis", "genesis": "genesis",
    "ex": "exodus", "exo": "exodus", "exodus": "exodus",
    "lev": "leviticus", "leviticus": "leviticus",
    "num": "numbers", "numbers": "numbers",
    "deut": "deuteronomy", "deuteronomy": "deuteronomy",
    "josh": "joshua", "joshua": "joshua",
    "judg": "judges", "judges": "judges",
    "ruth": "ruth",
    "1sam": "1samuel", "1 samuel": "1samuel", "1samuel": "1samuel",
    "2sam": "2samuel", "2 samuel": "2samuel", "2samuel": "2samuel",
    "1kgs": "1kings", "1 kings": "1kings", "1kings": "1kings",
    "2kgs": "2kings", "2 kings": "2kings", "2kings": "2kings",
    "1chr": "1chronicles", "1 chronicles": "1chronicles", "1chronicles": "1chronicles",
    "2chr": "2chronicles", "2 chronicles": "2chronicles", "2chronicles": "2chronicles",
    "ezra": "ezra", "neh": "nehemiah", "nehemiah": "nehemiah",
    "esther": "esther", "job": "job", "ps": "psalms", "psalm": "psalms", "psalms": "psalms",
    "prov": "proverbs", "proverbs": "proverbs", "eccl": "ecclesiastes", "ecclesiastes": "ecclesiastes",
    "song": "songofsolomon", "song of solomon": "songofsolomon", "songofsolomon": "songofsolomon",
    "isa": "isaiah", "isaiah": "isaiah", "jer": "jeremiah", "jeremiah": "jeremiah",
    "lam": "lamentations", "lamentations": "lamentations", "ezek": "ezekiel", "ezekiel": "ezekiel",
    "dan": "daniel", "daniel": "daniel", "hos": "hosea", "hosea": "hosea",
    "joel": "joel", "amos": "amos", "obad": "obadiah", "obadiah": "obadiah",
    "jonah": "jonah", "mic": "micah", "micah": "micah", "nah": "nahum", "nahum": "nahum",
    "hab": "habakkuk", "habakkuk": "habakkuk", "zeph": "zephaniah", "zephaniah": "zephaniah",
    "hag": "haggai", "haggai": "haggai", "zech": "zechariah", "zechariah": "zechariah",
    "mal": "malachi", "malachi": "malachi",
    "matt": "matthew", "matthew": "matthew", "mark": "mark", "luke": "luke", "john": "john",
    "acts": "acts", "rom": "romans", "romans": "romans",
    "1cor": "1corinthians", "1 corinthians": "1corinthians", "1corinthians": "1corinthians",
    "2cor": "2corinthians", "2 corinthians": "2corinthians", "2corinthians": "2corinthians",
    "gal": "galatians", "galatians": "galatians", "eph": "ephesians", "ephesians": "ephesians",
    "phil": "philippians", "philippians": "philippians", "col": "colossians", "colossians": "colossians",
    "1thess": "1thessalonians", "1 thessalonians": "1thessalonians", "1thessalonians": "1thessalonians",
    "2thess": "2thessalonians", "2 thessalonians": "2thessalonians", "2thessalonians": "2thessalonians",
    "1tim": "1timothy", "1 timothy": "1timothy", "1timothy": "1timothy",
    "2tim": "2timothy", "2 timothy": "2timothy", "2timothy": "2timothy",
    "titus": "titus", "philem": "philemon", "philemon": "philemon",
    "heb": "hebrews", "hebrews": "hebrews", "james": "james",
    "1pet": "1peter", "1 peter": "1peter", "1peter": "1peter",
    "2pet": "2peter", "2 peter": "2peter", "2peter": "2peter",
    "1john": "1john", "1 john": "1john", "2john": "2john", "2 john": "2john",
    "3john": "3john", "3 john": "3john", "jude": "jude", "rev": "revelation", "revelation": "revelation",
}

def normalize_book(book: object) -> str:
    text = str(book).strip().lower()
    text = " ".join(text.split())
    compact = text.replace(".", "")
    return BOOK_ALIASES.get(compact, compact.replace(" ", ""))

def ensure_target_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS verses(
            translation TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            strongs TEXT DEFAULT '',
            PRIMARY KEY (translation, book, chapter, verse)
        )
        '''
    )
    conn.commit()

def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [r[0] for r in rows]

def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [r[1] for r in rows]

def describe(conn: sqlite3.Connection) -> None:
    for table in list_tables(conn):
        cols = table_columns(conn, table)
        print(f"{table}: {', '.join(cols)}")

def fetch_joined_rows(conn: sqlite3.Connection, translation_hint: str):
    upper = translation_hint.upper()
    books_table = f"{upper}_books"
    verses_table = f"{upper}_verses"
    tables = set(list_tables(conn))
    if books_table not in tables or verses_table not in tables:
        raise RuntimeError(f"Expected tables {books_table} and {verses_table} not found.")

    vcols = table_columns(conn, verses_table)
    bcols = table_columns(conn, books_table)

    if vcols[:5] == ["id", "book_id", "chapter", "verse", "text"] and bcols[:2] == ["id", "name"]:
        query = f'''
            SELECT b.name, v.chapter, v.verse, v.text
            FROM "{verses_table}" v
            JOIN "{books_table}" b ON v.book_id = b.id
            ORDER BY v.book_id, v.chapter, v.verse
        '''
        for row in conn.execute(query):
            yield normalize_book(row[0]), int(row[1]), int(row[2]), str(row[3]).strip()
        return

    raise RuntimeError(
        f"Recognized normalized tables but unsupported columns. "
        f"{books_table}: {bcols}; {verses_table}: {vcols}"
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="Import Bible verses from normalized Scrollmapper SQLite DBs into the Ultimate Bible App DB.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", default=str(DEFAULT_TARGET_DB))
    parser.add_argument("--translation", required=True)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--list-tables", action="store_true")
    parser.add_argument("--describe", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()
    translation = args.translation.strip().lower()

    if not source.exists():
        raise SystemExit(f"Missing source DB: {source}")

    source_conn = sqlite3.connect(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    target_conn = sqlite3.connect(target)

    if args.list_tables:
        for name in list_tables(source_conn):
            print(name)
        return 0

    if args.describe:
        describe(source_conn)
        return 0

    ensure_target_schema(target_conn)

    if args.replace:
        target_conn.execute("DELETE FROM verses WHERE translation=?", (translation,))
        target_conn.commit()
        print(f"Deleted existing rows for translation={translation}")

    inserted = 0
    batch = []

    for book, chapter, verse, text in fetch_joined_rows(source_conn, translation):
        if not book or not text:
            continue
        batch.append((translation, book, chapter, verse, text, ""))
        if len(batch) >= 1000:
            target_conn.executemany(
                '''
                INSERT INTO verses (translation, book, chapter, verse, text, strongs)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(translation, book, chapter, verse)
                DO UPDATE SET text=excluded.text, strongs=excluded.strongs
                ''',
                batch,
            )
            inserted += len(batch)
            batch.clear()

    if batch:
        target_conn.executemany(
            '''
            INSERT INTO verses (translation, book, chapter, verse, text, strongs)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(translation, book, chapter, verse)
            DO UPDATE SET text=excluded.text, strongs=excluded.strongs
            ''',
            batch,
        )
        inserted += len(batch)

    target_conn.commit()
    source_conn.close()
    target_conn.close()
    print(f"Imported {inserted} rows into {target}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
