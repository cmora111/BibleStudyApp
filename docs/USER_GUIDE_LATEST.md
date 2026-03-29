# User Guide for the Latest Bundle

This bundle combines:
- stronger database initialization
- book-name normalization
- scholar token foundations
- starter Strong's dataset files
- setup wizard
- dataset import wizard

## Most useful commands

Initialize DB:

```bash
PYTHONPATH=. python scripts/init_db.py
```

Load demo scholar tokens:

```bash
PYTHONPATH=. python scripts/load_demo_scholar_tokens.py
```

Build starter Strong's bundle:

```bash
PYTHONPATH=. python scripts/build_strongs_dataset_bundle.py --out datasets/output
```
