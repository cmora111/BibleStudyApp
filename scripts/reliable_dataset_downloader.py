#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, re, shutil, sqlite3, urllib.error, urllib.request, zipfile
from pathlib import Path
from typing import Optional

DEFAULT_BASE = Path('/home/mora/Bible/BibleStudyApp/ultimate_bible_app_v7/output')
DEFAULT_DB = Path.home() / 'BibleStudy' / 'bible.db'
CHUNK_SIZE = 1024 * 1024

DATASETS = {
    'scrollmapper': {
        'url': 'https://github.com/scrollmapper/bible_databases/archive/refs/heads/master.zip',
        'filename': 'scrollmapper_bible_databases.zip',
    },
    'stepbible': {
        'url': 'https://github.com/STEPBible/STEPBible-Data/archive/refs/heads/master.zip',
        'filename': 'stepbible_data.zip',
    },
    'morphhb': {
        'url': 'https://github.com/openscriptures/morphhb/archive/refs/heads/master.zip',
        'filename': 'morphhb.zip',
    },
    'morphgnt': {
        'url': 'https://github.com/morphgnt/sblgnt/archive/refs/heads/master.zip',
        'filename': 'morphgnt_sblgnt.zip',
    },
    'geocoding': {
        'url': 'https://github.com/openbibleinfo/Bible-Geocoding-Data/archive/refs/heads/master.zip',
        'filename': 'bible_geocoding.zip',
    },
}

BOOK_ALIASES = {
    'gen': 'genesis', 'ge': 'genesis', 'gn': 'genesis',
    'ex': 'exodus', 'exo': 'exodus', 'lev': 'leviticus', 'lv': 'leviticus',
    'num': 'numbers', 'nm': 'numbers', 'deut': 'deuteronomy', 'dt': 'deuteronomy',
    'jos': 'joshua', 'josh': 'joshua', 'jdg': 'judges', 'judg': 'judges',
    'rut': 'ruth', '1sam': '1samuel', '2sam': '2samuel',
    '1kgs': '1kings', '2kgs': '2kings', '1chr': '1chronicles', '2chr': '2chronicles',
    'neh': 'nehemiah', 'est': 'esther', 'job': 'job', 'ps': 'psalms',
    'prov': 'proverbs', 'eccl': 'ecclesiastes', 'song': 'songofsolomon',
    'sos': 'songofsolomon', 'isa': 'isaiah', 'jer': 'jeremiah', 'lam': 'lamentations',
    'ezek': 'ezekiel', 'dan': 'daniel', 'hos': 'hosea', 'joel': 'joel', 'amos': 'amos',
    'obad': 'obadiah', 'jon': 'jonah', 'mic': 'micah', 'nah': 'nahum', 'hab': 'habakkuk',
    'zep': 'zephaniah', 'hag': 'haggai', 'zec': 'zechariah', 'mal': 'malachi',
    'matt': 'matthew', 'mt': 'matthew', 'mk': 'mark', 'mrk': 'mark', 'lk': 'luke',
    'jn': 'john', 'jhn': 'john', 'rom': 'romans', '1cor': '1corinthians',
    '2cor': '2corinthians', 'gal': 'galatians', 'eph': 'ephesians',
    'phil': 'philippians', 'col': 'colossians', '1th': '1thessalonians',
    '2th': '2thessalonians', '1tim': '1timothy', '2tim': '2timothy', 'tit': 'titus',
    'phlm': 'philemon', 'heb': 'hebrews', 'jas': 'james', 'jam': 'james',
    '1pet': '1peter', '2pet': '2peter', '1jn': '1john', '2jn': '2john',
    '3jn': '3john', 'jud': 'jude', 'rev': 'revelation',
}

VERSE_PATTERNS = [
    re.compile(r'^([1-3]?\s?[A-Za-z][A-Za-z\s]+?)\s+(\d+):(\d+)\s+(.+)$'),
    re.compile(r'^([1-3]?[A-Za-z]+)\s+(\d+):(\d+)\s+(.+)$'),
]

def log(msg: str) -> None:
    print(msg, flush=True)

def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def ensure_dirs(base: Path) -> dict[str, Path]:
    dirs = {
        'base': base,
        'downloads': base / 'downloads',
        'tmp': base / 'tmp',
        'bibles': base / 'bibles',
        'lexicons': base / 'lexicons',
        'greek': base / 'greek',
        'hebrew': base / 'hebrew',
        'crossrefs': base / 'crossrefs',
        'geography': base / 'geography',
        'manifests': base / 'manifests',
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs

def free_space_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024 ** 3)

def download_with_resume(url: str, dest: Path) -> Path:
    tmp = dest.with_suffix(dest.suffix + '.part')
    existing = tmp.stat().st_size if tmp.exists() else 0
    headers = {'User-Agent': 'UltimateBibleAppDatasetDownloader/1.0'}
    if existing:
        headers['Range'] = f'bytes={existing}-'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            status = getattr(resp, 'status', 200)
            mode = 'ab' if existing and status == 206 else 'wb'
            if mode == 'wb' and existing:
                existing = 0
            total = resp.headers.get('Content-Length')
            total_bytes = int(total) + existing if total else None
            with open(tmp, mode) as out:
                downloaded = existing
                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes:
                        pct = downloaded * 100 / total_bytes
                        print(f'\rDownloading {dest.name}: {downloaded/1e6:.1f} MB / {total_bytes/1e6:.1f} MB ({pct:.1f}%)', end='', flush=True)
                    else:
                        print(f'\rDownloading {dest.name}: {downloaded/1e6:.1f} MB', end='', flush=True)
        print()
    except urllib.error.HTTPError as e:
        if e.code == 416 and tmp.exists():
            tmp.rename(dest)
            return dest
        raise
    tmp.rename(dest)
    return dest

def extract_zip(zip_path: Path, out_dir: Path) -> Path:
    target = out_dir / zip_path.stem
    target.mkdir(parents=True, exist_ok=True)
    stamp = target / '.extracted'
    if stamp.exists():
        return target
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(target)
    stamp.write_text('ok', encoding='utf-8')
    return target

def normalize_book(book: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9 ]+', '', book).strip().lower()
    compact = cleaned.replace(' ', '')
    return BOOK_ALIASES.get(compact, compact)

def parse_human_line(line: str) -> Optional[tuple[str, int, int, str]]:
    line = line.strip()
    for pattern in VERSE_PATTERNS:
        m = pattern.match(line)
        if m:
            try:
                ch = int(m.group(2)); vs = int(m.group(3))
            except ValueError:
                return None
            return normalize_book(m.group(1)), ch, vs, m.group(4).strip()
    return None

def write_manifest_row(manifest_path: Path, row: dict) -> None:
    exists = manifest_path.exists()
    fields = ['dataset', 'source', 'output', 'rows', 'sha256']
    with open(manifest_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)

def convert_scrollmapper_csvs(extracted: Path, out_dir: Path, manifest: Path) -> int:
    count = 0
    for src in extracted.rglob('*.csv'):
        name = src.stem.lower()
        if name in {'kjv', 'web', 'asv', 'bbe', 'oeb'} or 'english' in str(src).lower():
            out = out_dir / f'{src.stem.lower()}.csv'
            rows = 0
            with open(src, 'r', encoding='utf-8', errors='ignore', newline='') as inp, open(out, 'w', encoding='utf-8', newline='') as out_f:
                reader = csv.DictReader(inp)
                writer = csv.writer(out_f)
                writer.writerow(['translation', 'book', 'chapter', 'verse', 'text', 'strongs'])
                for row in reader:
                    book = normalize_book(row.get('book', ''))
                    chapter = row.get('chapter'); verse = row.get('verse')
                    text = row.get('text', '').strip()
                    if not book or not chapter or not verse or not text:
                        continue
                    tr = src.stem.lower()
                    writer.writerow([tr, book, chapter, verse, text, row.get('strongs', '')])
                    rows += 1
            if rows:
                write_manifest_row(manifest, {'dataset': 'scrollmapper', 'source': str(src), 'output': str(out), 'rows': rows, 'sha256': sha256sum(out)})
                count += 1
    return count

def convert_tsvs(extracted: Path, out_dir: Path, manifest: Path, dataset: str) -> int:
    produced = 0
    for src in extracted.rglob('*.tsv'):
        out = out_dir / f'{src.stem.lower()}.csv'
        with open(src, 'r', encoding='utf-8', errors='ignore', newline='') as inp, open(out, 'w', encoding='utf-8', newline='') as out_f:
            reader = csv.reader(inp, delimiter='\t')
            rows = list(reader)
            if not rows:
                continue
            max_cols = max(len(r) for r in rows)
            writer = csv.writer(out_f)
            writer.writerow([f'col_{i+1}' for i in range(max_cols)])
            for row in rows:
                writer.writerow(row + [''] * (max_cols - len(row)))
        write_manifest_row(manifest, {'dataset': dataset, 'source': str(src), 'output': str(out), 'rows': sum(1 for _ in open(out, 'r', encoding='utf-8')) - 1, 'sha256': sha256sum(out)})
        produced += 1
    return produced

def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS verses(translation TEXT, book TEXT, chapter INTEGER, verse INTEGER, text TEXT, strongs TEXT DEFAULT "")')
    cur.execute('CREATE TABLE IF NOT EXISTS strongs(strongs TEXT PRIMARY KEY, lemma TEXT, transliteration TEXT, definition TEXT)')
    conn.commit()
    return conn

def import_bible_csv(csv_path: Path, db_path: Path) -> int:
    conn = connect_db(db_path)
    cur = conn.cursor()
    inserted = 0
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cur.execute(
                    'INSERT INTO verses (translation, book, chapter, verse, text, strongs) VALUES (?, ?, ?, ?, ?, ?)',
                    (row['translation'], row['book'], int(row['chapter']), int(row['verse']), row['text'], row.get('strongs', ''))
                )
                inserted += 1
            except Exception:
                continue
    conn.commit(); conn.close()
    return inserted

def build(base: Path, import_into_db: bool, db_path: Path) -> None:
    dirs = ensure_dirs(base)
    if free_space_gb(base) < 2.0:
        raise SystemExit(f'Not enough free space under {base}. Need about 2 GB free.')

    manifest = dirs['manifests'] / 'datasets_manifest.csv'
    if manifest.exists():
        manifest.unlink()

    summary = []
    for name, cfg in DATASETS.items():
        log(f'Preparing {name}')
        archive = download_with_resume(cfg['url'], dirs['downloads'] / cfg['filename'])
        extracted = extract_zip(archive, dirs['tmp'])
        summary.append({'dataset': name, 'archive': str(archive), 'extracted': str(extracted)})

        if name == 'scrollmapper':
            made = convert_scrollmapper_csvs(extracted, dirs['bibles'], manifest)
            log(f'Built {made} Bible CSV files from {name}')
        elif name == 'stepbible':
            made = convert_tsvs(extracted, dirs['lexicons'], manifest, name)
            log(f'Built {made} lexicon/research CSV files from {name}')
        elif name == 'morphhb':
            made = convert_tsvs(extracted, dirs['hebrew'], manifest, name)
            log(f'Built {made} Hebrew CSV files from {name}')
        elif name == 'morphgnt':
            made = convert_tsvs(extracted, dirs['greek'], manifest, name)
            log(f'Built {made} Greek CSV files from {name}')
        elif name == 'geocoding':
            made = convert_tsvs(extracted, dirs['geography'], manifest, name)
            log(f'Built {made} geography CSV files from {name}')

    (dirs['manifests'] / 'report.json').write_text(json.dumps({
        'base': str(base),
        'downloads': summary,
        'free_space_gb': round(free_space_gb(base), 2),
    }, indent=2), encoding='utf-8')

    if import_into_db:
        total = 0
        for csv_file in dirs['bibles'].glob('*.csv'):
            inserted = import_bible_csv(csv_file, db_path)
            total += inserted
            log(f'Imported {inserted} verses from {csv_file.name}')
        log(f'Total imported verses: {total}')

def main() -> int:
    parser = argparse.ArgumentParser(description='Reliable dataset downloader and builder for Ultimate Bible App.')
    parser.add_argument('--base', default=str(DEFAULT_BASE), help='Base output folder')
    parser.add_argument('--import-into-db', action='store_true', help='Import built Bible CSV files into SQLite')
    parser.add_argument('--db', default=str(DEFAULT_DB), help='SQLite database path')
    args = parser.parse_args()
    build(Path(args.base).expanduser().resolve(), args.import_into_db, Path(args.db).expanduser().resolve())
    log('Done.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
