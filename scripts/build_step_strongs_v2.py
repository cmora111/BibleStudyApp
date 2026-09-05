#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from import_stepbible_lexicon_v2 import parse_step_file


DEFAULT_LEXICON_DIR = (
    Path("datasets")
    / "source"
    / "STEPBible-Data"
    / "Lexicons"
)

DEFAULT_OUTPUT = (
    Path("datasets")
    / "output"
    / "strongs_v2_test.db"
)


SCHEMA = """
CREATE TABLE strongs_senses (
    estrong          TEXT NOT NULL,
    dstrong          TEXT NOT NULL,
    ustrong          TEXT NOT NULL,
    lemma            TEXT NOT NULL,
    transliteration  TEXT NOT NULL,
    morph            TEXT NOT NULL,
    gloss            TEXT NOT NULL,
    definition       TEXT NOT NULL,
    language         TEXT NOT NULL,
    source           TEXT NOT NULL,
    source_ordinal   INTEGER NOT NULL,

    PRIMARY KEY (estrong, dstrong)
);

CREATE INDEX idx_strongs_senses_estrong
    ON strongs_senses (estrong);

CREATE INDEX idx_strongs_senses_ustrong
    ON strongs_senses (ustrong);

CREATE INDEX idx_strongs_senses_language
    ON strongs_senses (language);
"""


def find_sources(lexicon_dir: Path) -> list[tuple[str, Path]]:
    greek = list(lexicon_dir.glob("TBESG*"))
    hebrew = list(lexicon_dir.glob("TBESH*"))

    if len(greek) != 1:
        raise RuntimeError(
            f"Expected exactly one TBESG source; found {len(greek)}"
        )

    if len(hebrew) != 1:
        raise RuntimeError(
            f"Expected exactly one TBESH source; found {len(hebrew)}"
        )

    return [
        ("greek", greek[0]),
        ("hebrew", hebrew[0]),
    ]


def build_database(
    output: Path,
    lexicon_dir: Path,
) -> None:
    sources = find_sources(lexicon_dir)

    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        output.unlink()

    conn = sqlite3.connect(output)

    try:
        conn.executescript(SCHEMA)

        total = 0

        for language, path in sources:
            print(f"Reading {language}: {path}")

            source_name = path.name
            language_count = 0

            for ordinal, entry in enumerate(
                parse_step_file(path),
                start=1,
            ):
                conn.execute(
                    """
                    INSERT INTO strongs_senses (
                        estrong,
                        dstrong,
                        ustrong,
                        lemma,
                        transliteration,
                        morph,
                        gloss,
                        definition,
                        language,
                        source,
                        source_ordinal
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.estrong,
                        entry.dstrong,
                        entry.ustrong,
                        entry.lemma,
                        entry.transliteration,
                        entry.morph,
                        entry.gloss,
                        entry.definition,
                        language,
                        source_name,
                        ordinal,
                    ),
                )

                language_count += 1
                total += 1

            print(
                f"  imported {language_count:,} "
                f"{language} records"
            )

        conn.commit()

        db_total = conn.execute(
            "SELECT COUNT(*) FROM strongs_senses"
        ).fetchone()[0]

        natural_keys = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT estrong, dstrong
                FROM strongs_senses
                GROUP BY estrong, dstrong
            )
            """
        ).fetchone()[0]

        estrongs = conn.execute(
            """
            SELECT COUNT(DISTINCT estrong)
            FROM strongs_senses
            """
        ).fetchone()[0]

        greek_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM strongs_senses
            WHERE language = 'greek'
            """
        ).fetchone()[0]

        hebrew_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM strongs_senses
            WHERE language = 'hebrew'
            """
        ).fetchone()[0]

        print()
        print("=== BUILD VALIDATION ===")
        print(f"Parser records:       {total:,}")
        print(f"Database records:     {db_total:,}")
        print(f"Natural keys:         {natural_keys:,}")
        print(f"Unique eStrong IDs:   {estrongs:,}")
        print(f"Greek records:        {greek_count:,}")
        print(f"Hebrew records:       {hebrew_count:,}")

        if total != db_total:
            raise RuntimeError(
                f"Row loss detected: parser={total}, db={db_total}"
            )

        if db_total != natural_keys:
            raise RuntimeError(
                "Natural-key collision detected after import"
            )

        print()
        print("Lossless STEP import validation: PASS")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    print()
    print(f"Created: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a disposable v2 STEP Strong's database "
            "without modifying the application database."
        )
    )

    parser.add_argument(
        "--lexicon-dir",
        type=Path,
        default=DEFAULT_LEXICON_DIR,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    build_database(
        output=args.output,
        lexicon_dir=args.lexicon_dir,
    )


if __name__ == "__main__":
    main()
