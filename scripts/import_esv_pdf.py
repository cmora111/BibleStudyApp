i#!/usr/bin/env python3

import subprocess
import sqlite3
import re
from pathlib import Path

PDF = Path("ESV.pdf")
RAW = Path("esv_raw.txt")

DB = Path.home() / "UltimateBibleApp/data/bible.db"

BOOK_MAP = {
"gen":"genesis","exo":"exodus","lev":"leviticus","num":"numbers","deu":"deuteronomy",
"jos":"joshua","jdg":"judges","rut":"ruth","1sa":"1samuel","2sa":"2samuel",
"1ki":"1kings","2ki":"2kings","1ch":"1chronicles","2ch":"2chronicles",
"ezr":"ezra","neh":"nehemiah","est":"esther","job":"job","ps":"psalms",
"pro":"proverbs","ecc":"ecclesiastes","sol":"songofsolomon","isa":"isaiah",
"jer":"jeremiah","lam":"lamentations","eze":"ezekiel","dan":"daniel",
"hos":"hosea","joe":"joel","amo":"amos","oba":"obadiah","jon":"jonah",
"mic":"micah","nah":"nahum","hab":"habakkuk","zep":"zephaniah",
"hag":"haggai","zec":"zechariah","mal":"malachi","mat":"matthew",
"mar":"mark","luk":"luke","joh":"john","act":"acts","rom":"romans",
"1co":"1corinthians","2co":"2corinthians","gal":"galatians","eph":"ephesians",
"phi":"philippians","col":"colossians","1th":"1thessalonians","2th":"2thessalonians",
"1ti":"1timothy","2ti":"2timothy","tit":"titus","phm":"philemon",
"heb":"hebrews","jam":"james","1pe":"1peter","2pe":"2peter",
"1jo":"1john","2jo":"2john","3jo":"3john","jud":"jude","rev":"revelation"
}

VERSE_RE = re.compile(r'^([1-3]?\s?[A-Za-z]+)\s+(\d+):(\d+)\s+(.*)$')

def normalize_book(book):

    key = book.lower().replace(" ", "")

    return BOOK_MAP.get(key, key)


def extract_pdf():

    print("Extracting PDF text...")

    subprocess.run([
        "mutool","draw",
        "-F","txt",
        "-o",str(RAW),
        str(PDF)
    ],check=True)


def parse_verses():

    verses = []

    current = None

    lines = RAW.read_text(errors="ignore").splitlines()

    for line in lines:

        line=line.strip()

        if not line:
            continue

        m = VERSE_RE.match(line)

        if m:

            if current:
                verses.append(current)

            book = normalize_book(m.group(1))

            chapter = int(m.group(2))

            verse = int(m.group(3))

            text = m.group(4)

            current = ("esv",book,chapter,verse,text)

        else:

            if current:
                current = (
                    current[0],
                    current[1],
                    current[2],
                    current[3],
                    current[4] + " " + line
                )

    if current:
        verses.append(current)

    return verses


def import_db(rows):

    print("Importing into database...")

    conn = sqlite3.connect(DB)

    cur = conn.cursor()

    cur.execute("DELETE FROM verses WHERE translation='esv'")

    cur.executemany(
        """
        INSERT INTO verses (translation,book,chapter,verse,text)
        VALUES (?,?,?,?,?)
        """,
        rows
    )

    conn.commit()

    conn.close()


def main():

    if not PDF.exists():
        print("Missing ESV.pdf")
        return

    extract_pdf()

    verses = parse_verses()

    print("Parsed verses:",len(verses))

    import_db(verses)

    print("ESV installed successfully.")


if __name__=="__main__":
    main()
