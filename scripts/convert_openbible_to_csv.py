#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

BOOK_MAP = {
    "Gen": "Genesis",
    "Exod": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deut": "Deuteronomy",
    "Josh": "Joshua",
    "Judg": "Judges",
    "Ruth": "Ruth",
    "1Sam": "1 Samuel",
    "2Sam": "2 Samuel",
    "1Kgs": "1 Kings",
    "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles",
    "2Chr": "2 Chronicles",
    "Ezra": "Ezra",
    "Neh": "Nehemiah",
    "Esth": "Esther",
    "Job": "Job",
    "Ps": "Psalms",
    "Prov": "Proverbs",
    "Eccl": "Ecclesiastes",
    "Song": "Song of Solomon",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Ezek": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obad": "Obadiah",
    "Jonah": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zeph": "Zephaniah",
    "Hag": "Haggai",
    "Zech": "Zechariah",
    "Mal": "Malachi",
    "Matt": "Matthew",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Rom": "Romans",
    "1Cor": "1 Corinthians",
    "2Cor": "2 Corinthians",
    "Gal": "Galatians",
    "Eph": "Ephesians",
    "Phil": "Philippians",
    "Col": "Colossians",
    "1Thess": "1 Thessalonians",
    "2Thess": "2 Thessalonians",
    "1Tim": "1 Timothy",
    "2Tim": "2 Timothy",
    "Titus": "Titus",
    "Phlm": "Philemon",
    "Heb": "Hebrews",
    "Jas": "James",
    "1Pet": "1 Peter",
    "2Pet": "2 Peter",
    "1John": "1 John",
    "2John": "2 John",
    "3John": "3 John",
    "Jude": "Jude",
    "Rev": "Revelation",
}

REF_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")
RANGE_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)-([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")


def convert_single_ref(ref: str) -> tuple[str, int, int]:
    ref = ref.strip()
    m = REF_RE.match(ref)
    if not m:
        raise ValueError(f"Bad ref: {ref}")
    book_code, chapter_s, verse_s = m.groups()
    book_name = BOOK_MAP.get(book_code)
    if not book_name:
        raise ValueError(f"Unknown book code: {book_code}")
    return book_name, int(chapter_s), int(verse_s)


def format_ref(book: str, chapter: int, verse: int) -> str:
    return f"{book} {chapter}:{verse}"


def expand_target_ref(ref: str) -> list[str]:
    ref = ref.strip()

    m = REF_RE.match(ref)
    if m:
        book, chapter, verse = convert_single_ref(ref)
        return [format_ref(book, chapter, verse)]

    m = RANGE_RE.match(ref)
    if m:
        start_book_code, start_ch_s, start_vs_s, end_book_code, end_ch_s, end_vs_s = m.groups()

        start_book = BOOK_MAP.get(start_book_code)
        end_book = BOOK_MAP.get(end_book_code)
        if not start_book or not end_book:
            raise ValueError(f"Unknown range book code in: {ref}")

        start_ch = int(start_ch_s)
        start_vs = int(start_vs_s)
        end_ch = int(end_ch_s)
        end_vs = int(end_vs_s)

        # only expand same-book same-chapter ranges safely
        if start_book == end_book and start_ch == end_ch and start_vs <= end_vs:
            return [format_ref(start_book, start_ch, v) for v in range(start_vs, end_vs + 1)]

        # fallback: keep first verse only for cross-chapter/cross-book ranges
        return [format_ref(start_book, start_ch, start_vs)]

    raise ValueError(f"Unsupported target ref: {ref}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_openbible_to_csv.py openbible.txt [output.csv]")
        return

    input_path = Path(sys.argv[1]).expanduser().resolve()
    output_path = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) > 2 else Path("openbible_crossrefs.csv")

    if not input_path.exists():
        print(f"File not found: {input_path}")
        return

    total = 0
    skipped = 0

    with input_path.open("r", encoding="utf-8") as f_in, output_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(
            f_out,
            fieldnames=["source_ref", "target_ref", "votes", "dataset", "note"]
        )
        writer.writeheader()

        for line in f_in:
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            # Skip header/comment rows
            if parts and parts[0] == "From Verse":
                continue
            if len(parts) != 3:
                skipped += 1
                continue

            source_ref_raw, target_ref_raw, weight_str = parts

            try:
                src_book, src_ch, src_vs = convert_single_ref(source_ref_raw)
                source_ref = format_ref(src_book, src_ch, src_vs)

                targets = expand_target_ref(target_ref_raw)

                weight = float(weight_str)
                votes = int(weight * 100)
            except Exception:
                skipped += 1
                continue

            for target_ref in targets:
                writer.writerow({
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "votes": votes,
                    "dataset": "openbible",
                    "note": ""
                })
                total += 1

    print(f"Converted {total} cross references")
    print(f"Skipped {skipped} lines")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
