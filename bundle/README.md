# Recommended Bible CSV Bundle Starter

This bundle does **not include the datasets themselves**.
It includes a manifest and downloader/converter scripts that fetch open/public datasets
and normalize them into CSV files for your Bible app.

## Included targets
- WEB (World English Bible) plain text -> CSV
- Scrollmapper Bible Databases ZIP -> copy selected CSVs
- STEPBible data ZIP -> convert selected TSV files to CSV
- OpenBible Geocoding ZIP -> convert CSV/TSV/JSON where possible into CSV outputs

## Quick start

```bash
python fetch_and_build_bundle.py --out ./output
```

This creates:

```text
output/
  bibles/
  lexicons/
  greek/
  hebrew/
  crossrefs/
  geography/
  manifest.csv
```

## Notes
- Public/open sources only.
- ESV is not included.
- Some upstream repositories may change filenames over time. If that happens, update the mapping section near the top of the script.
