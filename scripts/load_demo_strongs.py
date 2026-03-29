from pathlib import Path

from app.core.bible_db import BibleDB
from app.core.importers import parse_strongs_csv


def main() -> None:
    db = BibleDB()
    entries = list(parse_strongs_csv(Path("app/data/demo_strongs.csv")))
    total = db.bulk_import_strongs(entries)
    print(f"Loaded {total} Strong's demo entries.")


if __name__ == "__main__":
    main()
