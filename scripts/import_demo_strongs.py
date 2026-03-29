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
    db = BibleDB()
    path = ROOT / "app" / "data" / "demo_strongs.csv"
    entries = list(parse_strongs_file(path))
    imported = db.bulk_import_strongs(entries)
    print(f"Imported {imported} Strong's entries from {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
