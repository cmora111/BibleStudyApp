#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.bible_db import BibleDB, StrongsEntry


def detect_delimiter(line: str) -> str:
    if "\t" in line:
        return "\t"
    if "|" in line:
        return "|"
    return "\t"


def normalize_strongs(raw: str) -> str:
    raw = raw.strip()
    m = re.match(r"^([GH])\s*0*([0-9A-Za-z]+)$", raw, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}{m.group(2)}"
    return raw.upper()


def parse_step_lexicon(path: Path, language: str):
    first = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                first = line.rstrip("\n")
                break

    if not first:
        return

    delim = detect_delimiter(first)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delim)
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue

            row = [cell.strip() for cell in row]
            joined = " ".join(row).lower()

            if "strong" in joined and "lemma" in joined:
                continue

            strongs_id = row[0] if len(row) > 0 else ""
            lemma = row[1] if len(row) > 1 else ""
            gloss = row[2] if len(row) > 2 else ""
            definition = row[3] if len(row) > 3 else gloss

            strongs_id = normalize_strongs(strongs_id)

            if not strongs_id or not re.match(r"^[GH][0-9A-Za-z]+$", strongs_id):
                continue

            yield StrongsEntry(
                strongs_id=strongs_id,
                lemma=lemma,
                transliteration="",
                language=language,
                gloss=gloss,
                definition=definition,
            )


def merge_entries(*iterables):
    seen = set()
    for iterable in iterables:
        for entry in iterable:
            sid = entry.strongs_id
            if sid in seen:
                continue
            seen.add(sid)
            yield entry


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage:")
        print("  PYTHONPATH=. python scripts/import_stepbible_lexicon_fixed.py <greek_file> <hebrew_file>")
        return 1

    greek_file = Path(sys.argv[1]).expanduser().resolve()
    hebrew_file = Path(sys.argv[2]).expanduser().resolve()

    if not greek_file.exists():
        print(f"Missing Greek file: {greek_file}")
        return 1
    if not hebrew_file.exists():
        print(f"Missing Hebrew file: {hebrew_file}")
        return 1

    greek_entries = parse_step_lexicon(greek_file, "greek")
    hebrew_entries = parse_step_lexicon(hebrew_file, "hebrew")
    entries = list(merge_entries(greek_entries, hebrew_entries))

    db = BibleDB()
    imported = db.bulk_import_strongs(entries)
    print(f"Imported {imported} Strong's entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
