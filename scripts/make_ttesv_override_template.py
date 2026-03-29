#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/make_ttesv_override_template.py /path/to/ttesv_real_mismatches.csv")
        return 1

    source = Path(sys.argv[1]).expanduser().resolve()
    if not source.exists():
        print(f"Missing file: {source}")
        return 1

    out_csv = Path.cwd() / "ttesv_token_overrides_template.csv"

    with source.open("r", newline="", encoding="utf-8") as f_in, out_csv.open("w", newline="", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(
            f_out,
            fieldnames=[
                "book", "chapter", "verse",
                "action",
                "replacement_tokens",
                "position_override",
                "notes",
            ],
        )
        writer.writeheader()
        for row in reader:
            writer.writerow({
                "book": row["book"],
                "chapter": row["chapter"],
                "verse": row["verse"],
                "action": "",
                "replacement_tokens": "",
                "position_override": "",
                "notes": "",
            })

    print(f"Override template written to: {out_csv}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
