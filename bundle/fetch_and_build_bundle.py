#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

WEB_URL = "https://ebible.org/eng-web/webtxt.zip"
#SCROLLMAPPER_URL = "https://github.com/scrollmapper/bible_databases/archive/refs/heads/master.zip"
#STEP_URL = "https://github.com/STEPBible/STEPBible-Data/archive/refs/heads/master.zip"
#GEO_URL = "https://github.com/openbibleinfo/Bible-Geocoding-Data/archive/refs/heads/main.zip"

BOOK_ALIASES = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
    "exo": "Exodus", "ex": "Exodus",
    "lev": "Leviticus", "num": "Numbers", "deut": "Deuteronomy",
    "josh": "Joshua", "judg": "Judges", "rut": "Ruth",
    "1sam": "1 Samuel", "2sam": "2 Samuel", "1kgs": "1 Kings", "2kgs": "2 Kings",
    "1chr": "1 Chronicles", "2chr": "2 Chronicles", "neh": "Nehemiah",
    "est": "Esther", "job": "Job", "ps": "Psalms", "prov": "Proverbs",
    "eccl": "Ecclesiastes", "song": "Song of Solomon", "isa": "Isaiah",
    "jer": "Jeremiah", "lam": "Lamentations", "ezek": "Ezekiel", "dan": "Daniel",
    "hos": "Hosea", "obad": "Obadiah", "jon": "Jonah", "mic": "Micah",
    "nah": "Nahum", "hab": "Habakkuk", "zep": "Zephaniah", "hag": "Haggai",
    "zec": "Zechariah", "mal": "Malachi", "matt": "Matthew", "mrk": "Mark",
    "mk": "Mark", "lk": "Luke", "jn": "John", "rom": "Romans",
    "1cor": "1 Corinthians", "2cor": "2 Corinthians", "gal": "Galatians",
    "eph": "Ephesians", "phil": "Philippians", "col": "Colossians",
    "1th": "1 Thessalonians", "2th": "2 Thessalonians", "1tim": "1 Timothy",
    "2tim": "2 Timothy", "tit": "Titus", "phlm": "Philemon", "heb": "Hebrews",
    "jas": "James", "1pet": "1 Peter", "2pet": "2 Peter", "1jn": "1 John",
    "2jn": "2 John", "3jn": "3 John", "jud": "Jude", "rev": "Revelation",
}

VERSE_PATTERNS = [
    re.compile(r"^([1-3]?\\s?[A-Za-z][A-Za-z\\s]+?)\\s+(\\d+):(\\d+)\\s+(.+)$"),
    re.compile(r"^([1-3]?[A-Za-z]+)\\s+(\\d+):(\\d+)\\s+(.+)$"),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    urllib.request.urlretrieve(url, dest)
    return dest


def unzip(path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        zf.extractall(out_dir)


def normalize_book(book: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9 ]+", "", book).strip().lower()
    compact = clean.replace(" ", "")
    return BOOK_ALIASES.get(compact, clean.title())


def convert_web_to_csv(source_txt: Path, out_csv: Path) -> int:
    count = 0
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(source_txt, "r", encoding="utf-8", errors="ignore") as inp, open(out_csv, "w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["translation", "book", "chapter", "verse", "text", "strongs"])
        for line in inp:
            text = line.strip()
            if not text:
                continue
            matched = None
            for pat in VERSE_PATTERNS:
                m = pat.match(text)
                if m:
                    matched = m
                    break
            if not matched:
                continue
            book = normalize_book(matched.group(1))
            chapter = matched.group(2)
            verse = matched.group(3)
            verse_text = matched.group(4)
            writer.writerow(["web", book, chapter, verse, verse_text, ""])
            count += 1
    return count


def copy_scrollmapper_csvs(root: Path, out_dir: Path) -> int:
    count = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in root.rglob("*.csv"):
        lname = path.name.lower()
        if lname in {"kjv.csv", "asv.csv", "web.csv", "bbe.csv", "oebus.csv", "oebcth.csv"}:
            shutil.copy2(path, out_dir / path.name)
            count += 1
    return count


def convert_tsv_to_csv(tsv_path: Path, out_csv: Path) -> int:
    rows = 0
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(tsv_path, "r", encoding="utf-8", errors="ignore", newline="") as inp, open(out_csv, "w", encoding="utf-8", newline="") as out:
        reader = csv.reader(inp, delimiter='\t')
        writer = csv.writer(out)
        for row in reader:
            writer.writerow(row)
            rows += 1
    return rows


def convert_geo_json_to_csv(json_path: Path, out_csv: Path) -> int:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows = 0
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["name", "lat", "lon", "extra"])
        if isinstance(data, dict):
            items = data.items()
        else:
            items = []
        for key, value in items:
            if isinstance(value, dict):
                lat = value.get("lat") or value.get("latitude") or ""
                lon = value.get("lon") or value.get("lng") or value.get("longitude") or ""
                writer.writerow([key, lat, lon, json.dumps(value, ensure_ascii=False)])
                rows += 1
    return rows


def build(out_root: Path) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    for folder in ["bibles", "lexicons", "greek", "hebrew", "crossrefs", "geography", "downloads", "tmp"]:
        (out_root / folder).mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path("/home/mora/Bible/BibleStudyApp/ultimate_bible_app_v7/output/tmp")
        tmp.mkdir(parents=True, exist_ok=True)
#        tmp = Path(tmpdir)

        web_zip = download(WEB_URL, tmp / "web.zip")
        unzip(web_zip, tmp / "web")
        web_txt = None
        for cand in (tmp / "web").rglob("webtxt.txt"):
            web_txt = cand
            break
        if web_txt:
            rows = convert_web_to_csv(web_txt, out_root / "bibles" / "web.csv")
            log(f"WEB rows: {rows}")

        sm_zip = download(SCROLLMAPPER_URL, tmp / "scrollmapper.zip")
        unzip(sm_zip, tmp / "scrollmapper")
        copied = copy_scrollmapper_csvs(tmp / "scrollmapper", out_root / "bibles")
        log(f"Scrollmapper CSVs copied: {copied}")

        step_zip = download(STEP_URL, tmp / "step.zip")
        unzip(step_zip, tmp / "step")
        for path in (tmp / "step").rglob("*.tsv"):
            rel_name = path.stem.lower()
            target_dir = out_root / "lexicons"
            if "greek" in rel_name or "gnt" in rel_name:
                target_dir = out_root / "greek"
            elif "hebrew" in rel_name or "ot" in rel_name or "hb" in rel_name:
                target_dir = out_root / "hebrew"
            convert_tsv_to_csv(path, target_dir / f"{path.stem}.csv")

        geo_zip = download(GEO_URL, tmp / "geo.zip")
        unzip(geo_zip, tmp / "geo")
        for path in (tmp / "geo").rglob("*.csv"):
            shutil.copy2(path, out_root / "geography" / path.name)
        for path in (tmp / "geo").rglob("*.tsv"):
            convert_tsv_to_csv(path, out_root / "geography" / f"{path.stem}.csv")
        for path in (tmp / "geo").rglob("*.json"):
            try:
                convert_geo_json_to_csv(path, out_root / "geography" / f"{path.stem}.csv")
            except Exception:
                pass

    manifest = out_root / "manifest.csv"
    with open(manifest, "w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["category", "path"])
        for path in sorted(out_root.rglob("*.csv")):
            if path.name == "manifest.csv":
                continue
            writer.writerow([path.parent.name, str(path.relative_to(out_root))])
    log(f"Built bundle at {out_root}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="./output")
    args = parser.parse_args()
    build(Path(args.out).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
