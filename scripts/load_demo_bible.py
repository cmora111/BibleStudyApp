from pathlib import Path

from app.core.bible_db import BibleDB
from app.core.importers import parse_pipe_file


DEMO_FILES = [
    Path("app/data/demo_kjv.txt"),
    Path("app/data/demo_web.txt"),
    Path("app/data/demo_asv.txt"),
]


def main() -> None:
    db = BibleDB()
    total = 0
    for demo in DEMO_FILES:
        records = list(parse_pipe_file(demo, translation=demo.stem.replace("demo_", "")))
        total += db.bulk_import(records)
    print(f"Loaded {total} demo verses.")


if __name__ == "__main__":
    main()
