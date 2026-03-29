#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv
from pathlib import Path

def write_demo_lexicon(out_dir: Path) -> None:
    rows = [
        ["strongs_id","lemma","transliteration","language","definition"],
        ["G25","agapao","agapao","Greek","to love; to value, esteem, and show sacrificial love"],
        ["G26","agape","agape","Greek","love; self-giving love"],
        ["G2316","theos","theos","Greek","God; deity"],
        ["G4903","synergeo","synergeo","Greek","to work together, cooperate, assist in producing a result"],
        ["H430","elohim","elohim","Hebrew","God, gods, rulers"],
        ["H7225","reshith","reshith","Hebrew","beginning, first, chief, choice part"],
    ]
    with open(out_dir / "strongs_lexicon_demo.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

def write_demo_alignment(out_dir: Path) -> None:
    rows = [
        ["translation","book","chapter","verse","token_index","token_text","strongs_id","lemma","morph","source_lang","source_surface"],
        ["esv","romans",8,28,2,"know","G1492","oida","V-RAI-1P","grc","οἴδαμεν"],
        ["esv","romans",8,28,7,"love","G25","agapao","V-PAP-DPM","grc","ἀγαπῶσιν"],
        ["esv","romans",8,28,8,"God","G2316","theos","N-ASM","grc","θεόν"],
        ["esv","romans",8,28,11,"work","G4903","synergeo","V-PAI-3S","grc","συνεργεῖ"],
    ]
    with open(out_dir / "alignment_demo.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a starter Strong's dataset bundle.")
    parser.add_argument("--out", default="datasets/output")
    args = parser.parse_args()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_demo_lexicon(out_dir)
    write_demo_alignment(out_dir)
    print(f"Wrote starter Strong's bundle to {out_dir}")
