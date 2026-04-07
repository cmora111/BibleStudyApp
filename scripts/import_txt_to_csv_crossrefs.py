#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

BOOK_MAP = {
    "Gen": "genesis", "Exod": "exodus", "Lev": "leviticus", "Num": "numbers", "Deut": "deuteronomy",
    "Josh": "joshua", "Judg": "judges", "Ruth": "ruth", "1Sam": "1samuel", "2Sam": "2samuel",
    "1Kgs": "1kings", "2Kgs": "2kings", "1Chr": "1chronicles", "2Chr": "2chronicles", "Ezra": "ezra",
    "Neh": "nehemiah", "Esth": "esther", "Job": "job", "Ps": "psalms", "Prov": "proverbs",
    "Eccl": "ecclesiastes", "Song": "songofsolomon", "Isa": "isaiah", "Jer": "jeremiah",
    "Lam": "lamentations", "Ezek": "ezekiel", "Dan": "daniel", "Hos": "hosea", "Joel": "joel",
    "Amos": "amos", "Obad": "obadiah", "Jonah": "jonah", "Mic": "micah", "Nah": "nahum",
    "Hab": "habakkuk", "Zeph": "zephaniah", "Hag": "haggai", "Zech": "zechariah", "Mal": "malachi",
    "Matt": "matthew", "Mark": "mark", "Luke": "luke", "John": "john", "Acts": "acts",
    "Rom": "romans", "1Cor": "1corinthians", "2Cor": "2corinthians", "Gal": "galatians",
    "Eph": "ephesians", "Phil": "philippians", "Col": "colossians", "1Thess": "1thessalonians",
    "2Thess": "2thessalonians", "1Tim": "1timothy", "2Tim": "2timothy", "Titus": "titus",
    "Phlm": "philemon", "Heb": "hebrews", "Jas": "james", "1Pet": "1peter", "2Pet": "2peter",
    "1John": "1john", "2John": "2john", "3John": "3john", "Jude": "jude", "Rev": "revelation",
}

REF_RE = re.compile(r'^(?P<book>[1-3]?[A-Za-z]+)\.(?P<chapter>\d+)\.(?P<verse>\d+)$')

def parse_ref(ref: str) -> tuple[str, int, int]:
    ref = (ref or "").strip()
    m = REF_RE.match(ref)
    if not m:
        raise ValueError(f"Unsupported verse format: {ref}")
    book_token = m.group("book")
    chapter = int(m.group("chapter"))
    verse = int(m.group("verse"))
    book = BOOK_MAP.get(book_token)
    if not book:
        raise ValueError(f"Unknown book token: {book_token}")
    return book, chapter, verse

def parse_ref_or_range(value: str) -> dict:
    value = (value or "").strip()
    if "-" in value:
        left, right = value.split("-", 1)
        sb, sc, sv = parse_ref(left)
        eb, ec, ev = parse_ref(right)
        return {
            "raw_ref": value,
            "book_start": sb,
            "chapter_start": sc,
            "verse_start": sv,
            "book_end": eb,
            "chapter_end": ec,
            "verse_end": ev,
            "is_range": True,
        }
    b, c, v = parse_ref(value)
    return {
        "raw_ref": value,
        "book_start": b,
        "chapter_start": c,
        "verse_start": v,
        "book_end": b,
        "chapter_end": c,
        "verse_end": v,
        "is_range": False,
    }

def convert_crossrefs_txt_to_csv(input_path: Path, output_path: Path) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    converted = 0
    skipped = 0
    with input_path.open("r", encoding="utf-8", errors="replace", newline="") as src, output_path.open("w", encoding="utf-8", newline="") as dst:
        reader = csv.DictReader(src, delimiter="\t")
        fieldnames = [
            "source_ref",
            "source_book",
            "source_chapter",
            "source_verse",
            "target_ref",
            "target_book_start",
            "target_chapter_start",
            "target_verse_start",
            "target_book_end",
            "target_chapter_end",
            "target_verse_end",
            "target_is_range",
            "votes",
        ]
        writer = csv.DictWriter(dst, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            try:
                from_ref = (row.get("From Verse") or "").strip()
                to_ref = (row.get("To Verse") or "").strip()
                votes_raw = (row.get("Votes") or "0").strip()
                source_book, source_chapter, source_verse = parse_ref(from_ref)
                target = parse_ref_or_range(to_ref)
                writer.writerow({
                    "source_ref": from_ref,
                    "source_book": source_book,
                    "source_chapter": source_chapter,
                    "source_verse": source_verse,
                    "target_ref": to_ref,
                    "target_book_start": target["book_start"],
                    "target_chapter_start": target["chapter_start"],
                    "target_verse_start": target["verse_start"],
                    "target_book_end": target["book_end"],
                    "target_chapter_end": target["chapter_end"],
                    "target_verse_end": target["verse_end"],
                    "target_is_range": int(target["is_range"]),
                    "votes": int(votes_raw),
                })
                converted += 1
            except Exception:
                skipped += 1
    return converted, skipped

def main():
    parser = argparse.ArgumentParser(description="Convert OpenBible-style cross references TSV into app-friendly CSV.")
    parser.add_argument("input", nargs="?", default="cross_references.txt")
    parser.add_argument("output", nargs="?", default="output/crossrefs/openbible_crossrefs.csv")
    args = parser.parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")
    converted, skipped = convert_crossrefs_txt_to_csv(input_path, output_path)
    print(f"Converted: {converted}")
    print(f"Skipped: {skipped}")
    print(f"Output: {output_path}")

if __name__ == "__main__":
    main()
