#!/usr/bin/env python3

import csv
import re
from pathlib import Path

INPUT = Path("esv_raw.txt")
OUTPUT = Path("esv.csv")

BOOK_MAP = {
    "Gen": "genesis", "Exod": "exodus", "Lev": "leviticus", "Num": "numbers",
    "Deut": "deuteronomy", "Josh": "joshua", "Judg": "judges", "Ruth": "ruth",
    "1Sam": "1samuel", "2Sam": "2samuel", "1Kgs": "1kings", "2Kgs": "2kings",
    "1Chr": "1chronicles", "2Chr": "2chronicles", "Ezra": "ezra", "Neh": "nehemiah",
    "Esth": "esther", "Job": "job", "Ps": "psalms", "Prov": "proverbs",
    "Eccl": "ecclesiastes", "Song": "songofsolomon", "Isa": "isaiah",
    "Jer": "jeremiah", "Lam": "lamentations", "Ezek": "ezekiel", "Dan": "daniel",
    "Hos": "hosea", "Joel": "joel", "Amos": "amos", "Obad": "obadiah",
    "Jonah": "jonah", "Mic": "micah", "Nah": "nahum", "Hab": "habakkuk",
    "Zeph": "zephaniah", "Hag": "haggai", "Zech": "zechariah", "Mal": "malachi",
    "Matt": "matthew", "Mark": "mark", "Luke": "luke", "John": "john",
    "Acts": "acts", "Rom": "romans", "1Cor": "1corinthians", "2Cor": "2corinthians",
    "Gal": "galatians", "Eph": "ephesians", "Phil": "philippians",
    "Col": "colossians", "1Thess": "1thessalonians", "2Thess": "2thessalonians",
    "1Tim": "1timothy", "2Tim": "2timothy", "Titus": "titus", "Phlm": "philemon",
    "Heb": "hebrews", "Jas": "james", "1Pet": "1peter", "2Pet": "2peter",
    "1John": "1john", "2John": "2john", "3John": "3john", "Jude": "jude",
    "Rev": "revelation",
}

VERSE_RE = re.compile(r'^([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\s+(.*)$')

def clean_text(text: str) -> str:
    text = text.replace("\x0c", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    if not INPUT.exists():
        print("Missing esv_raw.txt")
        return

    lines = INPUT.read_text(encoding="utf-8", errors="ignore").splitlines()

    rows = []
    current = None

    def flush_current():
        nonlocal current
        if current is None:
            return
        translation, book, chapter, verse, text = current
        text = clean_text(text)
        if book != "unknown" and text:
            rows.append((translation, book, chapter, verse, text))
        current = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        m = VERSE_RE.match(line)
        if m:
            flush_current()
            book_abbr = m.group(1)
            chapter = int(m.group(2))
            verse = int(m.group(3))
            text = m.group(4).strip()
            book = BOOK_MAP.get(book_abbr, "unknown")
            current = ("esv", book, chapter, verse, text)
        else:
            # continuation line for wrapped verse text
            if current is not None:
                current = (
                    current[0],
                    current[1],
                    current[2],
                    current[3],
                    current[4] + " " + line,
                )

    flush_current()

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["translation", "book", "chapter", "verse", "text"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} verses to {OUTPUT}")

if __name__ == "__main__":
    main()
