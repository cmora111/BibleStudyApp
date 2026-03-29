from __future__ import annotations

import argparse
from pathlib import Path

from app.core.bible_db import BibleDB
from app.core.importers import parse_strongs_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a licensed Strong's lexicon file into the Ultimate Bible App database.")
    parser.add_argument("path", help="Path to Strong's CSV or JSONL file")
    parser.add_argument("--format", choices=["csv", "jsonl"], help="Override detected format")
    args = parser.parse_args()

    db = BibleDB()
    path = Path(args.path)
    entries = list(parse_strongs_file(path, fmt=args.format))
    imported = db.bulk_import_strongs(entries)
    print(f"Imported {imported} Strong's entries from {path}")


if __name__ == "__main__":
    main()
