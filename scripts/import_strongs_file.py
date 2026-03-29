#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.bible_db import BibleDB
from app.core.importers import parse_strongs_file

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python scripts/import_strongs_file.py /path/to/strongs.csv")
        return 1

    file_path = Path(sys.argv[1]).expanduser().resolve()
    if not file_path.exists():
        print(f"Missing file: {file_path}")
        return 1

    db = BibleDB()
    entries = list(parse_strongs_file(file_path))
    imported = db.bulk_import_strongs(entries)
    print(f"Imported {imported} Strong's entries from {file_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
