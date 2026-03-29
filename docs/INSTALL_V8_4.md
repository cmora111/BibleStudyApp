# Install Guide for v8.4

v8.4 adds an in-app setup wizard.

## Copy files into your project

```bash
cp app/core/setup_tasks.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_3/app/core/
cp app/ui/setup_wizard.py ~/Bible/BibleStudyApp/ultimate_bible_app_v8_3/app/ui/
```

## Wire it into your main window

In `app/ui/main_window.py`, add:

```python
from app.ui.setup_wizard import SetupWizardWindow
```

Add a menu item or button like:

```python
tools_menu.add_command(label="Setup Wizard", command=self.open_setup_wizard)
```

Add method:

```python
def open_setup_wizard(self):
    SetupWizardWindow(self.root, Path.cwd())
```
