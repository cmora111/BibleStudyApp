from __future__ import annotations

import argparse
from pathlib import Path

from app.core.bible_db import BibleDB
from app.core.importers import parse_bible_file, parse_bible_folder


def main() -> None:
    parser = argparse.ArgumentParser(description="Import licensed Bible datasets into the Ultimate Bible App database.")
    parser.add_argument("path", help="Path to a Bible file or folder")
    parser.add_argument("--translation", help="Override translation code for single-file imports")
    parser.add_argument("--format", choices=["pipe", "csv", "jsonl"], help="Override detected file format")
    args = parser.parse_args()

    db = BibleDB()
    path = Path(args.path)
    if path.is_dir():
        records = list(parse_bible_folder(path))
    else:
        records = list(parse_bible_file(path, translation=args.translation, fmt=args.format))
    imported = db.bulk_import(records)
    print(f"Imported {imported} verses from {path}")


if __name__ == "__main__":
    main()
