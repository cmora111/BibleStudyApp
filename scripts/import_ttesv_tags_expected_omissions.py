#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import DB_FILE

TTESV_RE = re.compile(r'^\$([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\t(.*)$')
MAP_RE = re.compile(r'(\d+(?:\+\d+)*)=<(\d+)>')

BOOK_MAP = {
    "Gen": "genesis", "Exo": "exodus", "Lev": "leviticus", "Num": "numbers",
    "Deu": "deuteronomy", "Jos": "joshua", "Jdg": "judges", "Rut": "ruth",
    "1Sa": "1samuel", "2Sa": "2samuel", "1Ki": "1kings", "2Ki": "2kings",
    "1Ch": "1chronicles", "2Ch": "2chronicles", "Ezr": "ezra", "Neh": "nehemiah",
    "Est": "esther", "Job": "job", "Psa": "psalms", "Pro": "proverbs",
    "Ecc": "ecclesiastes", "Sng": "songofsolomon", "Song": "songofsolomon",
    "Isa": "isaiah", "Jer": "jeremiah", "Lam": "lamentations", "Eze": "ezekiel",
    "Ezek": "ezekiel", "Dan": "daniel", "Hos": "hosea", "Joe": "joel", "Joel": "joel",
    "Amo": "amos", "Oba": "obadiah", "Jon": "jonah", "Mic": "micah", "Nah": "nahum",
    "Hab": "habakkuk", "Zep": "zephaniah", "Hag": "haggai", "Zec": "zechariah",
    "Mal": "malachi", "Mat": "matthew", "Mrk": "mark", "Luk": "luke", "Jhn": "john",
    "Act": "acts", "Rom": "romans", "1Co": "1corinthians", "2Co": "2corinthians",
    "Gal": "galatians", "Eph": "ephesians", "Php": "philippians", "Col": "colossians",
    "1Th": "1thessalonians", "2Th": "2thessalonians", "1Ti": "1timothy", "2Ti": "2timothy",
    "Tit": "titus", "Phm": "philemon", "Heb": "hebrews", "Jas": "james",
    "1Pe": "1peter", "2Pe": "2peter", "1Jn": "1john", "2Jn": "2john",
    "3Jn": "3john", "Jud": "jude", "Rev": "revelation",
}

POSITION_BUFFER = 3

EXPECTED_OMISSIONS = {
    ("matthew", 12, 47), ("matthew", 17, 21), ("matthew", 18, 11), ("matthew", 23, 14),
    ("mark", 7, 16), ("mark", 9, 44), ("mark", 9, 46), ("mark", 11, 26), ("mark", 15, 28),
    ("luke", 17, 36), ("luke", 23, 17), ("john", 5, 4), ("acts", 8, 37), ("acts", 15, 34),
    ("acts", 24, 7), ("acts", 28, 29), ("romans", 16, 24),
}

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

def fetch_esv_verse(conn: sqlite3.Connection, book: str, chapter: int, verse: int) -> str | None:
    row = conn.execute(
        """
        SELECT text
        FROM verses
        WHERE translation='esv' AND book=? AND chapter=? AND verse=?
        """,
        (book, chapter, verse),
    ).fetchone()
    return row[0] if row else None

def tokenize(text: str) -> list[str]:
    text = text.replace("’", "'")

    rough = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[.,:;!?()\"]", text)
    out: list[str] = []

    for tok in rough:
        # keep comma-grouped numbers together, e.g. 8,580 or 32,500
        if re.fullmatch(r"\d+(?:,\d+)+", tok):
            out.append(tok)
            continue

        # split hyphenated compounds into parts
        if "-" in tok:
            parts = [p for p in tok.split("-") if p]
            out.extend(parts)
            continue

        # split possessive/apostrophe forms: Jacob's -> Jacob, s
        m = re.fullmatch(r"([A-Za-z0-9]+)'([A-Za-z0-9]+)", tok)
        if m:
            out.append(m.group(1))
            out.append(m.group(2))
            continue

        out.append(tok)

    return out

def parse_mapping_blob(blob: str, token_count: int | None = None) -> tuple[dict[int, str], int]:
    mapping: dict[int, str] = {}
    ignored = 0
    for m in MAP_RE.finditer(blob):
        positions = m.group(1).split("+")
        strongs = f"G{int(m.group(2))}"
        for pos in positions:
            p = int(pos)
            if token_count is not None and p > token_count + POSITION_BUFFER:
                ignored += 1
                continue
            mapping[p] = strongs
    return mapping, ignored

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/import_ttesv_tags.py /path/to/TTESV.txt")
        return 1

    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.exists():
        print(f"Missing file: {source}")
        return 1

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    conn.execute("DELETE FROM verse_token_tags WHERE translation='esv'")
    conn.commit()

    inserted = 0
    skipped = 0
    psalm_superscriptions = 0
    expected_omissions = 0
    unmatched = 0
    ignored_positions = 0
    missing_book_map = 0
    missing_esv_other = 0

    with source.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.startswith("$"):
                continue

            m = TTESV_RE.match(line)
            if not m:
                continue

            short_book, chapter_s, verse_s, blob = m.groups()
            chapter = int(chapter_s)
            verse = int(verse_s)

            book = BOOK_MAP.get(short_book)
            if not book:
                skipped += 1
                missing_book_map += 1
                continue

            if book == "psalms" and verse == 0:
                skipped += 1
                psalm_superscriptions += 1
                continue

            if (book, chapter, verse) in EXPECTED_OMISSIONS:
                skipped += 1
                expected_omissions += 1
                continue

            verse_text = fetch_esv_verse(conn, book, chapter, verse)
            if not verse_text:
                skipped += 1
                missing_esv_other += 1
                continue

            tokens = tokenize(verse_text)
            strongs_map, ignored = parse_mapping_blob(blob, token_count=len(tokens))
            ignored_positions += ignored

            if strongs_map and max(strongs_map) > len(tokens):
                unmatched += 1

            rows = []
            for i, token in enumerate(tokens, start=1):
                rows.append((
                    "esv",
                    book,
                    chapter,
                    verse,
                    i,
                    token,
                    strongs_map.get(i),
                    "",
                    "",
                ))

            conn.executemany(
                """
                INSERT OR REPLACE INTO verse_token_tags
                (translation, book, chapter, verse, token_index, token_text, strongs_id, lemma, gloss)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            inserted += len(rows)

    conn.commit()
    conn.close()

    print(f"Imported {inserted} ESV token tags")
    print(f"Skipped total: {skipped}")
    print(f"  Psalm superscriptions skipped: {psalm_superscriptions}")
    print(f"  Expected omissions skipped: {expected_omissions}")
    print(f"  Missing BOOK_MAP entries: {missing_book_map}")
    print(f"  Missing ESV verses (other): {missing_esv_other}")
    print(f"Potential real mismatches after filtering: {unmatched}")
    print(f"Ignored overflow positions: {ignored_positions}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
