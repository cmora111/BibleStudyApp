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

BOOK_MAP = {
    "Gen": "genesis", "Exo": "exodus", "Lev": "leviticus", "Num": "numbers",
    "Deu": "deuteronomy", "Jos": "joshua", "Jdg": "judges", "Rut": "ruth",
    "1Sa": "1samuel", "2Sa": "2samuel", "1Ki": "1kings", "2Ki": "2kings",
    "1Ch": "1chronicles", "2Ch": "2chronicles", "Ezr": "ezra", "Neh": "nehemiah",
    "Est": "esther", "Job": "job", "Psa": "psalms", "Pro": "proverbs",
    "Ecc": "ecclesiastes", "Song": "songofsolomon", "Isa": "isaiah", "Jer": "jeremiah",
    "Lam": "lamentations", "Ezek": "ezekiel", "Dan": "daniel", "Hos": "hosea",
    "Joel": "joel", "Amo": "amos", "Oba": "obadiah", "Jon": "jonah",
    "Mic": "micah", "Nah": "nahum", "Hab": "habakkuk", "Zep": "zephaniah",
    "Hag": "haggai", "Zec": "zechariah", "Mal": "malachi",
    "Mat": "matthew", "Mrk": "mark", "Luk": "luke", "Jhn": "john",
    "Act": "acts", "Rom": "romans", "1Co": "1corinthians", "2Co": "2corinthians",
    "Gal": "galatians", "Eph": "ephesians", "Php": "philippians", "Col": "colossians",
    "1Th": "1thessalonians", "2Th": "2thessalonians", "1Ti": "1timothy", "2Ti": "2timothy",
    "Tit": "titus", "Phm": "philemon", "Heb": "hebrews", "Jas": "james",
    "1Pe": "1peter", "2Pe": "2peter", "1Jn": "1john", "2Jn": "2john",
    "3Jn": "3john", "Jud": "jude", "Rev": "revelation",
}

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/audit_ttesv_skipped_verses.py /path/to/TTESV.txt")
        return 1

    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.exists():
        print(f"Missing file: {source}")
        return 1

    conn = sqlite3.connect(DB_FILE)

    total = 0
    skipped = 0
    missing_book_map = 0
    missing_esv = 0
    skipped_rows: list[str] = []

    with source.open("r", encoding="utf-8") as f:
        psalm_zero = 0
        for line in f:
            if not line.startswith("$"):
                continue

            m = TTESV_RE.match(line.rstrip("\n"))
            if not m:
                continue

            short_book, ch, vs, _blob = m.groups()
            total += 1

            book = BOOK_MAP.get(short_book)
            if book == "psalms" and int(vs) == 0:
                skipped += 1
                psalm_zero += 1
                continue
            if not book:
                skipped += 1
                missing_book_map += 1
                skipped_rows.append(f"{short_book} {ch}:{vs}\tmissing BOOK_MAP entry")
                continue

            row = conn.execute(
                "SELECT text FROM verses WHERE translation='esv' AND book=? AND chapter=? AND verse=?",
                (book, int(ch), int(vs)),
            ).fetchone()

            if not row:
                skipped += 1
                missing_esv += 1
                skipped_rows.append(f"{book} {ch}:{vs}\tmissing in verses table")
                continue

    conn.close()

    for item in skipped_rows[:500]:
        print(item)

    if len(skipped_rows) > 500:
        print(f"... truncated output, showing first 500 of {len(skipped_rows)} skipped verses")

    print(f"\nTotal TTESV verses scanned: {total}")
    print(f"Skipped verses: {skipped}")
    print(f"Missing BOOK_MAP entries: {missing_book_map}")
    print(f"Missing ESV verses in DB: {missing_esv}")
    print(f"Psalm superscriptions skipped: {psalm_zero}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
