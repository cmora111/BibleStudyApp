# Install Latest Full Bundle

## 1. Copy your working app to a new folder

```bash
cd ~/Bible/BibleStudyApp
cp -r ultimate_bible_app ultimate_bible_app_latest
```

## 2. Extract this bundle and run the installer

```bash
cd /path/to/ultimate_bible_app_latest_full_bundle/installer
bash apply_latest_patch.sh ~/Bible/BibleStudyApp/ultimate_bible_app_latest
```

## 3. Initialize the database with the improved script

```bash
cd ~/Bible/BibleStudyApp/ultimate_bible_app_latest
PYTHONPATH=. python scripts/init_db.py
```

Expected output includes:

```text
Database initialized
```
