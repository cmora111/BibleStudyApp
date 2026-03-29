#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.bible_db import BibleDB


def parse_stepbible_strongs(file_path: Path):
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            parts = line.strip().split("\t")

            # Adjust depending on file structure
            try:
                strongs_id = parts[0]
                lemma = parts[1]
                gloss = parts[2] if len(parts) > 2 else ""
                definition = parts[3] if len(parts) > 3 else ""
            except IndexError:
                continue

            yield {
                "strongs_id": strongs_id,
                "lemma": lemma,
                "transliteration": "",
                "language": "greek" if strongs_id.startswith("G") else "hebrew",
                "gloss": gloss,
                "definition": definition,
            }


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_stepbible_strongs.py <file>")
        return

    file_path = Path(sys.argv[1])

    db = BibleDB()
    entries = list(parse_stepbible_strongs(file_path))
    inserted = db.bulk_import_strongs(entries)

    print(f"Imported {inserted} Strong's entries")


if __name__ == "__main__":
    main()
