from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sqlite3
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

CHUNK_SIZE = 1024 * 1024

DATASETS = {
    "scrollmapper": {
        "label": "Bible translations bundle (KJV / WEB / ASV)",
        "url": "https://github.com/scrollmapper/bible_databases/archive/refs/heads/master.zip",
        "filename": "scrollmapper_bible_databases.zip",
        "kind": "zip",
        "category": "bibles",
    },
    "stepbible": {
        "label": "STEP Bible data (lexicons / research tables)",
        "url": "https://github.com/STEPBible/STEPBible-Data/archive/refs/heads/master.zip",
        "filename": "stepbible_data.zip",
        "kind": "zip",
        "category": "lexicons",
    },
    "morphhb": {
        "label": "Hebrew OT (Open Scriptures Hebrew Bible)",
        "url": "https://github.com/openscriptures/morphhb/archive/refs/heads/master.zip",
        "filename": "morphhb.zip",
        "kind": "zip",
        "category": "hebrew",
    },
    "morphgnt": {
        "label": "Greek NT (MorphGNT / SBLGNT)",
        "url": "https://github.com/morphgnt/sblgnt/archive/refs/heads/master.zip",
        "filename": "morphgnt_sblgnt.zip",
        "kind": "zip",
        "category": "greek",
    },
    "geocoding": {
        "label": "Bible geography / place data",
        "url": "https://github.com/openbibleinfo/Bible-Geocoding-Data/archive/refs/heads/master.zip",
        "filename": "bible_geocoding.zip",
        "kind": "zip",
        "category": "crossrefs",
    },
}

BOOK_ALIASES = {
    "gen": "genesis", "ge": "genesis", "gn": "genesis",
    "ex": "exodus", "exo": "exodus", "lev": "leviticus", "lv": "leviticus",
    "num": "numbers", "nm": "numbers", "deut": "deuteronomy", "dt": "deuteronomy",
    "jos": "joshua", "josh": "joshua", "jdg": "judges", "judg": "judges",
    "rut": "ruth", "1sam": "1samuel", "2sam": "2samuel",
    "1kgs": "1kings", "2kgs": "2kings", "1chr": "1chronicles", "2chr": "2chronicles",
    "neh": "nehemiah", "est": "esther", "job": "job", "ps": "psalms",
    "prov": "proverbs", "eccl": "ecclesiastes", "song": "songofsolomon",
    "sos": "songofsolomon", "isa": "isaiah", "jer": "jeremiah", "lam": "lamentations",
    "ezek": "ezekiel", "dan": "daniel", "hos": "hosea", "joel": "joel", "amos": "amos",
    "obad": "obadiah", "jon": "jonah", "mic": "micah", "nah": "nahum", "hab": "habakkuk",
    "zep": "zephaniah", "hag": "haggai", "zec": "zechariah", "mal": "malachi",
    "matt": "matthew", "mt": "matthew", "mk": "mark", "mrk": "mark", "lk": "luke",
    "jn": "john", "jhn": "john", "rom": "romans", "1cor": "1corinthians",
    "2cor": "2corinthians", "gal": "galatians", "eph": "ephesians",
    "phil": "philippians", "col": "colossians", "1th": "1thessalonians",
    "2th": "2thessalonians", "1tim": "1timothy", "2tim": "2timothy", "tit": "titus",
    "phlm": "philemon", "heb": "hebrews", "jas": "james", "jam": "james",
    "1pet": "1peter", "2pet": "2peter", "1jn": "1john", "2jn": "2john",
    "3jn": "3john", "jud": "jude", "rev": "revelation",
}

VERSE_PATTERNS = [
    re.compile(r"^([1-3]?\s?[A-Za-z][A-Za-z\s]+?)\s+(\d+):(\d+)\s+(.+)$"),
    re.compile(r"^([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\s+(.+)$"),
]


class DatasetManager:
    def __init__(self, base_dir: str | Path, db_path: str | Path | None = None):
        self.base_dir = Path(base_dir).expanduser().resolve()
        self.db_path = Path(db_path).expanduser().resolve() if db_path else None
        self.cancel_requested = False
        self.log_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[str], None]] = None

    def set_callbacks(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.log_callback = log_callback
        self.progress_callback = progress_callback

    def log(self, message: str) -> None:
        if self.log_callback:
            self.log_callback(message)

    def progress(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)
        self.log(message)

    def ensure_dirs(self) -> dict[str, Path]:
        dirs = {
            "base": self.base_dir,
            "downloads": self.base_dir / "downloads",
            "tmp": self.base_dir / "tmp",
            "bibles": self.base_dir / "bibles",
            "lexicons": self.base_dir / "lexicons",
            "greek": self.base_dir / "greek",
            "hebrew": self.base_dir / "hebrew",
            "crossrefs": self.base_dir / "crossrefs",
            "manifests": self.base_dir / "manifests",
        }
        for p in dirs.values():
            p.mkdir(parents=True, exist_ok=True)
        return dirs

    def free_space_gb(self) -> float:
        return shutil.disk_usage(self.base_dir).free / (1024 ** 3)

    def verify_disk_space(self, required_gb: float = 2.0) -> None:
        free = self.free_space_gb()
        if free < required_gb:
            raise RuntimeError(
                f"Not enough free space in {self.base_dir}. "
                f"Free: {free:.2f} GB, required: {required_gb:.2f} GB."
            )
        self.log(f"Disk space OK: {free:.2f} GB free")

    def sha256sum(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def download_with_resume(self, url: str, dest: Path) -> Path:
        tmp = dest.with_suffix(dest.suffix + ".part")
        existing = tmp.stat().st_size if tmp.exists() else 0

        headers = {"User-Agent": "UltimateBibleAppDatasetManager/1.0"}
        if existing:
            headers["Range"] = f"bytes={existing}-"

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as resp:
                status = getattr(resp, "status", 200)
                mode = "ab" if existing and status == 206 else "wb"
                if mode == "wb" and existing:
                    existing = 0

                total = resp.headers.get("Content-Length")
                total_bytes = int(total) + existing if total else None

                with open(tmp, mode) as out:
                    downloaded = existing
                    while True:
                        if self.cancel_requested:
                            raise RuntimeError("Download cancelled.")
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes:
                            pct = downloaded * 100 / total_bytes
                            self.progress(
                                f"{dest.name}: {downloaded/1e6:.1f} MB / "
                                f"{total_bytes/1e6:.1f} MB ({pct:.1f}%)"
                            )
                        else:
                            self.progress(f"{dest.name}: {downloaded/1e6:.1f} MB downloaded")
        except urllib.error.HTTPError as e:
            if e.code == 416 and tmp.exists():
                tmp.rename(dest)
                return dest
            raise

        tmp.rename(dest)
        return dest

    def extract_zip(self, zip_path: Path, out_dir: Path) -> Path:
        target = out_dir / zip_path.stem
        target.mkdir(parents=True, exist_ok=True)
        stamp = target / ".extracted"
        if stamp.exists():
            self.log(f"Already extracted: {zip_path.name}")
            return target
        self.log(f"Extracting {zip_path.name}")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target)
        stamp.write_text("ok", encoding="utf-8")
        return target

    def normalize_book(self, book: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 ]+", "", book).strip().lower()
        compact = cleaned.replace(" ", "")
        return BOOK_ALIASES.get(compact, compact)

    def write_manifest_row(self, manifest_path: Path, row: dict) -> None:
        exists = manifest_path.exists()
        fields = ["dataset", "source", "output", "rows", "sha256"]
        with open(manifest_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            if not exists:
                writer.writeheader()
            writer.writerow(row)

    def convert_scrollmapper_csvs(self, extracted: Path, out_dir: Path, manifest: Path) -> int:
        count = 0
        preferred = {"kjv", "web", "asv"}
        for src in extracted.rglob("*.csv"):
            name = src.stem.lower()
            if name not in preferred:
                continue

            out = out_dir / f"{name}.csv"
            rows = 0
            with open(src, "r", encoding="utf-8", errors="ignore", newline="") as inp, \
                 open(out, "w", encoding="utf-8", newline="") as out_f:
                reader = csv.DictReader(inp)
                writer = csv.writer(out_f)
                writer.writerow(["translation", "book", "chapter", "verse", "text", "strongs"])
                for row in reader:
                    book = self.normalize_book(row.get("book", ""))
                    chapter = row.get("chapter")
                    verse = row.get("verse")
                    text = row.get("text", "").strip()
                    if not book or not chapter or not verse or not text:
                        continue
                    writer.writerow([name, book, chapter, verse, text, row.get("strongs", "")])
                    rows += 1

            if rows:
                self.write_manifest_row(
                    manifest,
                    {
                        "dataset": "scrollmapper",
                        "source": str(src),
                        "output": str(out),
                        "rows": rows,
                        "sha256": self.sha256sum(out),
                    },
                )
                self.log(f"Built {out.name} with {rows} rows")
                count += 1
        return count

    def convert_tsvs(self, extracted: Path, out_dir: Path, manifest: Path, dataset: str) -> int:
        produced = 0
        for src in extracted.rglob("*.tsv"):
            out = out_dir / f"{src.stem.lower()}.csv"
            with open(src, "r", encoding="utf-8", errors="ignore", newline="") as inp, \
                 open(out, "w", encoding="utf-8", newline="") as out_f:
                reader = csv.reader(inp, delimiter="\t")
                rows = list(reader)
                if not rows:
                    continue
                max_cols = max(len(r) for r in rows)
                writer = csv.writer(out_f)
                writer.writerow([f"col_{i+1}" for i in range(max_cols)])
                for row in rows:
                    writer.writerow(row + [""] * (max_cols - len(row)))

            self.write_manifest_row(
                manifest,
                {
                    "dataset": dataset,
                    "source": str(src),
                    "output": str(out),
                    "rows": max(0, sum(1 for _ in open(out, "r", encoding="utf-8")) - 1),
                    "sha256": self.sha256sum(out),
                },
            )
            self.log(f"Built {out.name}")
            produced += 1
        return produced

    def connect_db(self) -> sqlite3.Connection:
        if self.db_path is None:
            raise RuntimeError("No database path configured.")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS verses(
                translation TEXT,
                book TEXT,
                chapter INTEGER,
                verse INTEGER,
                text TEXT,
                strongs TEXT DEFAULT ''
            )
            """
        )
        conn.commit()
        return conn

    def import_bible_csv(self, csv_path: Path) -> int:
        if self.db_path is None:
            return 0
        conn = self.connect_db()
        cur = conn.cursor()
        inserted = 0
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cur.execute(
                        """
                        INSERT INTO verses (translation, book, chapter, verse, text, strongs)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["translation"],
                            row["book"],
                            int(row["chapter"]),
                            int(row["verse"]),
                            row["text"],
                            row.get("strongs", ""),
                        ),
                    )
                    inserted += 1
                except Exception:
                    continue
        conn.commit()
        conn.close()
        return inserted

    def build_all(self, import_into_db: bool = False) -> None:
        self.cancel_requested = False
        dirs = self.ensure_dirs()
        self.verify_disk_space()

        manifest = dirs["manifests"] / "datasets_manifest.csv"
        if manifest.exists():
            manifest.unlink()

        report_rows = []

        for name, cfg in DATASETS.items():
            if self.cancel_requested:
                raise RuntimeError("Operation cancelled.")
            self.log(f"Preparing {cfg['label']}")
            archive = self.download_with_resume(cfg["url"], dirs["downloads"] / cfg["filename"])
            extracted = self.extract_zip(archive, dirs["tmp"])
            report_rows.append({"dataset": name, "archive": str(archive), "extracted": str(extracted)})

            if name == "scrollmapper":
                made = self.convert_scrollmapper_csvs(extracted, dirs["bibles"], manifest)
                self.log(f"Built {made} Bible CSV files")
            elif name == "stepbible":
                made = self.convert_tsvs(extracted, dirs["lexicons"], manifest, name)
                self.log(f"Built {made} STEP Bible CSV files")
            elif name == "morphhb":
                made = self.convert_tsvs(extracted, dirs["hebrew"], manifest, name)
                self.log(f"Built {made} Hebrew OT CSV files")
            elif name == "morphgnt":
                made = self.convert_tsvs(extracted, dirs["greek"], manifest, name)
                self.log(f"Built {made} Greek NT CSV files")
            elif name == "geocoding":
                made = self.convert_tsvs(extracted, dirs["crossrefs"], manifest, name)
                self.log(f"Built {made} cross-reference / geography CSV files")

        report = {
            "base": str(self.base_dir),
            "free_space_gb": round(self.free_space_gb(), 2),
            "datasets": report_rows,
        }
        (dirs["manifests"] / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

        if import_into_db and self.db_path is not None:
            total = 0
            for csv_file in dirs["bibles"].glob("*.csv"):
                inserted = self.import_bible_csv(csv_file)
                total += inserted
                self.log(f"Imported {inserted} verses from {csv_file.name}")
            self.log(f"Total imported verses: {total}")

    def run_in_thread(self, import_into_db: bool = False, on_done: Optional[Callable[[Optional[Exception]], None]] = None) -> threading.Thread:
        def worker():
            error = None
            try:
                self.build_all(import_into_db=import_into_db)
            except Exception as exc:  # noqa: BLE001
                error = exc
            if on_done:
                on_done(error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread
