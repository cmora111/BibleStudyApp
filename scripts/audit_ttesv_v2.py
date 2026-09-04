#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path

from app.core.config import DB_FILE


ROOT = Path(__file__).resolve().parents[1]

SOURCE = next(
    (ROOT / "datasets/source/STEPBible-Data/Tagged-Bibles").glob("TTESV*")
)

LINE_RE = re.compile(
    r'^\$([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\t(.*)$'
)

WORD_RE = re.compile(
    r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?"
)

FIELD_RE = re.compile(
    r'^(\d+(?:\+\d+)*)=((?:<\d+>)(?:\+<\d+>)*)$'
)

BOOK_MAP = {
    "Gen": "genesis", "Exo": "exodus", "Lev": "leviticus",
    "Num": "numbers", "Deu": "deuteronomy", "Jos": "joshua",
    "Jdg": "judges", "Rut": "ruth", "1Sa": "1samuel",
    "2Sa": "2samuel", "1Ki": "1kings", "2Ki": "2kings",
    "1Ch": "1chronicles", "2Ch": "2chronicles",
    "Ezr": "ezra", "Neh": "nehemiah", "Est": "esther",
    "Job": "job", "Psa": "psalms", "Pro": "proverbs",
    "Ecc": "ecclesiastes", "Sng": "songofsolomon",
    "Song": "songofsolomon", "Isa": "isaiah",
    "Jer": "jeremiah", "Lam": "lamentations",
    "Eze": "ezekiel", "Ezek": "ezekiel", "Dan": "daniel",
    "Hos": "hosea", "Joe": "joel", "Joel": "joel",
    "Amo": "amos", "Oba": "obadiah", "Jon": "jonah",
    "Mic": "micah", "Nah": "nahum", "Hab": "habakkuk",
    "Zep": "zephaniah", "Hag": "haggai",
    "Zec": "zechariah", "Mal": "malachi",

    "Mat": "matthew", "Mrk": "mark", "Luk": "luke",
    "Jhn": "john", "Act": "acts", "Rom": "romans",
    "1Co": "1corinthians", "2Co": "2corinthians",
    "Gal": "galatians", "Eph": "ephesians",
    "Php": "philippians", "Col": "colossians",
    "1Th": "1thessalonians", "2Th": "2thessalonians",
    "1Ti": "1timothy", "2Ti": "2timothy",
    "Tit": "titus", "Phm": "philemon", "Heb": "hebrews",
    "Jas": "james", "1Pe": "1peter", "2Pe": "2peter",
    "1Jn": "1john", "2Jn": "2john", "3Jn": "3john",
    "Jud": "jude", "Rev": "revelation",
}


def classify_strongs(raw: str) -> str:
    """
    Preserve TTESV's documented distinction.

    Hebrew: five digits beginning with zero
    Greek:  four digits
    Anything else: report instead of guessing.
    """
    if len(raw) == 5 and raw.startswith("0"):
        return f"H{int(raw)}"

    if len(raw) == 4:
        return f"G{int(raw)}"

    return f"?{raw}"


def fetch_esv(conn, book: str, chapter: int, verse: int):
    row = conn.execute(
        """
        SELECT text
        FROM verses
        WHERE translation='esv'
          AND book=?
          AND chapter=?
          AND verse=?
        """,
        (book, chapter, verse),
    ).fetchone()

    return row[0] if row else None


def main():
    conn = sqlite3.connect(DB_FILE)

    counts = Counter()

    out_of_range = []
    literal_number_candidates = []
    ambiguous_number_candidates = []
    unknown_strongs = []
    malformed_fields = []
    multi_strongs = []
    multi_positions = []

    with SOURCE.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            m = LINE_RE.match(line)
            if not m:
                continue

            short_book, chapter_s, verse_s, blob = m.groups()

            chapter = int(chapter_s)
            verse = int(verse_s)

            book = BOOK_MAP.get(short_book)
            if not book:
                counts["missing_book_map"] += 1
                continue

            text = fetch_esv(conn, book, chapter, verse)
            if text is None:
                counts["missing_esv_verse"] += 1
                continue

            counts["verses"] += 1

            words = WORD_RE.findall(text)
            numeric_words = {
                w.replace(",", "")
                for w in words
                if w.replace(",", "").isdigit()
            }

            fields = [
                field.strip()
                for field in blob.split("\t")
                if field.strip()
            ]

            for field in fields:
                fm = FIELD_RE.match(field)

                if not fm:
                    malformed_fields.append(
                        (book, chapter, verse, field)
                    )
                    counts["malformed_fields"] += 1
                    continue

                lhs, rhs = fm.groups()

                positions = [int(x) for x in lhs.split("+")]
                strongs_raw = re.findall(r'<(\d+)>', rhs)
                strongs = [
                    classify_strongs(s)
                    for s in strongs_raw
                ]

                counts["mapping_fields"] += 1
                counts["strongs_links"] += len(strongs)

                if len(positions) > 1:
                    counts["multi_position_fields"] += 1
                    multi_positions.append(
                        (
                            book, chapter, verse,
                            lhs, strongs, text
                        )
                    )

                if len(strongs) > 1:
                    counts["multi_strongs_fields"] += 1
                    multi_strongs.append(
                        (
                            book, chapter, verse,
                            lhs, strongs, text
                        )
                    )

                for sid in strongs:
                    if sid.startswith("?"):
                        counts["unknown_strongs_format"] += 1
                        unknown_strongs.append(
                            (
                                book, chapter, verse,
                                lhs, sid, field
                            )
                        )

                # Single-number LHS can be either a position or,
                # in some TTESV records, a literal number in the ESV.
                if len(positions) == 1:
                    p = positions[0]
                    literal = str(p)

                    if p > len(words):
                        if literal in numeric_words:
                            counts["literal_number_candidate"] += 1
                            literal_number_candidates.append(
                                (
                                    book, chapter, verse,
                                    literal, strongs,
                                    len(words), text
                                )
                            )
                        else:
                            counts["true_out_of_range"] += 1
                            out_of_range.append(
                                (
                                    book, chapter, verse,
                                    p, len(words),
                                    strongs, text
                                )
                            )

                    elif literal in numeric_words:
                        # Could legitimately be either position N
                        # or the literal number N.
                        counts["ambiguous_number_candidate"] += 1
                        ambiguous_number_candidates.append(
                            (
                                book, chapter, verse,
                                p, strongs, text
                            )
                        )

                else:
                    for p in positions:
                        if p > len(words):
                            counts["multi_position_out_of_range"] += 1

    conn.close()

    print(f"Source: {SOURCE}")
    print()
    print("=== COUNTS ===")

    for key in sorted(counts):
        print(f"{key:32} {counts[key]:,}")

    print()
    print("=== FIRST 20 LITERAL-NUMBER CANDIDATES ===")

    for row in literal_number_candidates[:20]:
        book, ch, vs, literal, strongs, wc, text = row
        print(
            f"{book} {ch}:{vs}: "
            f"literal={literal!r} "
            f"strongs={strongs} "
            f"word_count={wc}"
        )
        print(f"    {text}")

    print()
    print("=== FIRST 20 TRUE OUT-OF-RANGE ===")

    for row in out_of_range[:20]:
        book, ch, vs, pos, wc, strongs, text = row
        print(
            f"{book} {ch}:{vs}: "
            f"position={pos} "
            f"word_count={wc} "
            f"strongs={strongs}"
        )
        print(f"    {text}")

    print()
    print("=== FIRST 20 AMBIGUOUS NUMERIC LHS ===")

    for row in ambiguous_number_candidates[:20]:
        book, ch, vs, pos, strongs, text = row
        print(
            f"{book} {ch}:{vs}: "
            f"lhs={pos} "
            f"strongs={strongs}"
        )
        print(f"    {text}")

    print()
    print("=== FIRST 10 MULTI-STRONG'S FIELDS ===")

    for row in multi_strongs[:10]:
        book, ch, vs, lhs, strongs, text = row
        print(
            f"{book} {ch}:{vs}: "
            f"{lhs} -> {strongs}"
        )

    print()
    print("=== FIRST 10 UNKNOWN STRONG'S FORMATS ===")

    for row in unknown_strongs[:10]:
        print(row)

    print()
    print("=== FIRST 10 MALFORMED FIELDS ===")

    for row in malformed_fields[:10]:
        print(row)


if __name__ == "__main__":
    main()
