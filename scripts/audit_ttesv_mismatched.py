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

def parse_mapping_blob(blob: str, token_count: int | None = None):
    mapping = {}
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

def fetch_esv_verse(conn, book: str, chapter: int, verse: int):
    row = conn.execute(
        "SELECT text FROM verses WHERE translation='esv' AND book=? AND chapter=? AND verse=?",
        (book, chapter, verse),
    ).fetchone()
    return row[0] if row else None

def main():
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/audit_ttesv_real_mismatches.py /path/to/TTESV.txt")
        return 1

    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.exists():
        print(f"Missing file: {source}")
        return 1

    out_csv = Path.cwd() / "ttesv_real_mismatches.csv"
    conn = sqlite3.connect(DB_FILE)
    rows_out = []

    with source.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("$"):
                continue
            m = TTESV_RE.match(line.rstrip("\n"))
            if not m:
                continue
            short_book, ch_s, vs_s, blob = m.groups()
            chapter = int(ch_s)
            verse = int(vs_s)
            book = BOOK_MAP.get(short_book)
            if not book:
                continue
            if book == "psalms" and verse == 0:
                continue
            if (book, chapter, verse) in EXPECTED_OMISSIONS:
                continue

            verse_text = fetch_esv_verse(conn, book, chapter, verse)
            if not verse_text:
                continue

            tokens = tokenize(verse_text)
            strongs_map, ignored = parse_mapping_blob(blob, token_count=len(tokens))
            filtered_max = max(strongs_map) if strongs_map else 0

            if filtered_max > len(tokens):
                rows_out.append({
                    "book": book,
                    "chapter": chapter,
                    "verse": verse,
                    "token_count": len(tokens),
                    "filtered_max": filtered_max,
                    "gap": filtered_max - len(tokens),
                    "ignored_overflow_positions": ignored,
                    "verse_text": verse_text,
                    "tokens": " | ".join(f"{i}:{tok}" for i, tok in enumerate(tokens, start=1)),
                    "strongs_positions": " | ".join(f"{pos}:{sid}" for pos, sid in sorted(strongs_map.items())),
                })

    conn.close()

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "book", "chapter", "verse", "token_count", "filtered_max", "gap",
                "ignored_overflow_positions", "verse_text", "tokens", "strongs_positions"
            ],
        )
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Real mismatches exported: {len(rows_out)}")
    print(f"CSV written to: {out_csv}")
    for row in rows_out[:10]:
        print(f"{row['book']} {row['chapter']}:{row['verse']}  tokens={row['token_count']}  filtered_max={row['filtered_max']}  gap={row['gap']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
