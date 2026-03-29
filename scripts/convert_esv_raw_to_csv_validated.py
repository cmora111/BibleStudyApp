#!/usr/bin/env python3

import csv
import re
from pathlib import Path

INPUT = Path("esv_raw.txt")
OUTPUT = Path("esv.csv")
REJECTS = Path("esv_rejects.log")

VERSE_RE = re.compile(r'^(\d+):(\d+)\s+(.*)$')

def main():

    if not INPUT.exists():
        print("Missing esv_raw.txt")
        return

    rows = []
    rejects = []

    for line in INPUT.read_text(encoding="utf-8", errors="ignore").splitlines():

        line = line.strip()

        if not line:
            continue

        m = VERSE_RE.match(line)

        if not m:
            continue

        chapter = int(m.group(1))
        verse = int(m.group(2))
        text = m.group(3).strip()

        if len(text) < 10:
            rejects.append(line)
            continue

        rows.append(("esv","unknown",chapter,verse,text))

    with OUTPUT.open("w",newline="",encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "translation",
            "book",
            "chapter",
            "verse",
            "text"
        ])

        for r in rows:
            writer.writerow(r)

    REJECTS.write_text("\n".join(rejects))

    print("Wrote",len(rows),"verses to",OUTPUT)
    print("Rejected",len(rejects),"lines")

if __name__ == "__main__":
    main()
