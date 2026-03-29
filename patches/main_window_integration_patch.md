# main_window.py integration patch

Add this import near the top of `app/ui/main_window.py`:

```python
from app.ui.dataset_manager_window import DatasetManagerWindow
```

Then add this menu item where you build the Tools menu:

```python
tools.add_command(label="Dataset Manager", command=self.open_dataset_manager)
```

Add this method inside your main window class:

```python
def open_dataset_manager(self):
    DatasetManagerWindow(self.root)
```

## What this adds
- GUI Dataset Manager
- auto-downloads WEB, KJV, ASV
- downloads Greek NT + Hebrew OT
- downloads Strong's / STEP Bible lexicon tables
- downloads cross-reference / geography data
- resumes partial downloads
- verifies disk space before downloading
- optional import of WEB/KJV/ASV into SQLite after download
```
