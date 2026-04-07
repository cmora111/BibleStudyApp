
# Dataset Manager Patch

This starter patch adds a lightweight dataset manager to the app.

## Included files
- `app/engines/dataset_manager.py`
- `app/ui/DATASET_MANAGER_PATCH_SNIPPETS.py`

## What it does
- Tracks known datasets
- Checks whether expected files are installed
- Shows disk space
- Registers local files into expected target locations
- Stores a manifest at `output/dataset_manager_manifest.json`

## Suggested next integration
Wire the snippets into `main_window.py` and add a `Datasets` tab.

## Safe behavior
- no hardcoded remote downloads
- no destructive moves
- works with your clean Git workflow
