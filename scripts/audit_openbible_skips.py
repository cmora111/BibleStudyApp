#!/usr/bin/env python3
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

OPENBIBLE_REF_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")

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

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/audit_openbible_skips.py ~/Downloads/cross_references.txt")
        return 1

    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"Missing file: {path}")
        return 1

    unknown_codes = collections.Counter()
    bad_source = 0
    bad_target = 0
    bad_lines = 0
    examples = []

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")
            if len(parts) != 3:
                bad_lines += 1
                if len(examples) < 25:
                    examples.append((lineno, "bad_line", line))
                continue

            source_ref, target_ref, _weight = parts

            for kind, ref in [("source", source_ref), ("target", target_ref)]:
                m = OPENBIBLE_REF_RE.match(ref.strip())
                if not m:
                    if kind == "source":
                        bad_source += 1
                    else:
                        bad_target += 1
                    if len(examples) < 25:
                        examples.append((lineno, f"bad_{kind}", ref))
                    continue

                code = m.group(1)
                if code not in BOOK_MAP:
                    unknown_codes[code] += 1
                    if len(examples) < 25:
                        examples.append((lineno, f"unknown_{kind}_code", ref))

    print("Unknown book codes:")
    for code, count in unknown_codes.most_common():
        print(f"{code}\t{count}")

    print(f"\nBad source refs: {bad_source}")
    print(f"Bad target refs: {bad_target}")
    print(f"Bad lines: {bad_lines}")

    print("\nExamples:")
    for lineno, kind, value in examples:
        print(f"{lineno}\t{kind}\t{value}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
