from __future__ import annotations

DATASET_HINTS = {
    "STEPBible-Data-master.zip": {
        "purpose": "scholarly source data, lexicons, cross references, geography, original-language resources",
        "recommended_destination": "datasets/vendor/STEPBible-Data-master",
        "notes": [
            "Extract first; do not import the whole zip directly into SQLite.",
            "Use it as a source repository for lexicons, cross references, geography, and language data.",
            "Review licensing and individual subfolder formats before importing into your app tables.",
        ],
    },
    "bible_databases-master.zip": {
        "purpose": "prebuilt Bible databases and cross-reference databases",
        "recommended_destination": "datasets/vendor/bible_databases-master",
        "notes": [
            "Extract first.",
            "Use SQLite or CSV assets from the repository for Bible text and cross references.",
            "Good source for KJV/ASV/WEB imports and cross-reference extras.",
        ],
    },
    "Bible-Passage-Reference-Parser-master.zip": {
        "purpose": "reference parsing library, not Bible text data",
        "recommended_destination": "vendor/Bible-Passage-Reference-Parser-master",
        "notes": [
            "This is application logic, not verse data.",
            "Integrate it into parsing / reference detection features, not into the Bible database.",
        ],
    },
    "morphhb-master.zip": {
        "purpose": "Hebrew morphology / original-language data",
        "recommended_destination": "datasets/vendor/morphhb-master",
        "notes": [
            "Extract first.",
            "Use as a source for Hebrew morphology, lemmas, and original-language workflows.",
            "Map fields into scholar alignment / morphology tables, not directly into verses.",
        ],
    },
    "sblgnt-master.zip": {
        "purpose": "Greek New Testament text and morphology/alignment source",
        "recommended_destination": "datasets/vendor/sblgnt-master",
        "notes": [
            "Extract first.",
            "Use for scholar search, Greek token workflows, and morphology-backed study tools.",
            "Review the SBLGNT license terms before redistribution or bundling.",
        ],
    },
}

def explain_dataset(name: str) -> list[str]:
    if name in DATASET_HINTS:
        item = DATASET_HINTS[name]
        return [f"Dataset: {name}", f"Purpose: {item['purpose']}", f"Recommended destination: {item['recommended_destination']}", *item["notes"]]
    return [f"Dataset: {name}", "Extract it first, inspect the files, and import only the relevant assets."]
