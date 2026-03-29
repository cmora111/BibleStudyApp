# main_window.py fix + layout upgrade

Apply these changes to `app/ui/main_window.py`.

## 1) Fix the crash in default_translation()
Replace your current `default_translation()` with the version in `main_window_upgrade_snippets.py`.

Do **not** create any Tk widgets inside `default_translation()`.

## 2) Add the Dataset Manager import
Near the top of the file, add:

```python
from app.ui.dataset_manager_window import DatasetManagerWindow
```

## 3) Add these methods inside your main window class
Copy these methods from `main_window_upgrade_snippets.py` into your class:
- `read_current_chapter`
- `insert_clickable_reference`
- `insert_assistant_text_with_links`
- `open_reference_from_string`
- `open_reference_with_context`
- `open_dataset_manager`

## 4) Upgrade the layout so the middle pane is wider

### If you use `grid()`
Change:

```python
self.root.grid_columnconfigure(0, weight=1)
self.root.grid_columnconfigure(1, weight=1)
self.root.grid_columnconfigure(2, weight=1)
```

to:

```python
self.root.grid_columnconfigure(0, weight=1)
self.root.grid_columnconfigure(1, weight=3)
self.root.grid_columnconfigure(2, weight=1)
```

### If you use `pack()`
Use:

```python
left_frame.pack(side="left", fill="y")
middle_frame.pack(side="left", fill="both", expand=True)
right_frame.pack(side="left", fill="y")
```

and make the reader wider:

```python
self.reader = tk.Text(middle_frame, wrap="word", width=110)
```

## 5) Add a Translation dropdown in your UI build code
Put this in your controls area, not inside `default_translation()`:

```python
translations = self.db.translations()
tk.Label(parent, text="Translation").pack(side="left")
tk.OptionMenu(parent, self.translation_var, *translations).pack(side="left")
```

## 6) Add a Read Chapter button
Near your verse navigation controls:

```python
tk.Button(parent, text="Read Chapter", command=self.read_current_chapter).pack(side="left")
```

## 7) Add Dataset Manager to Tools menu
Where you build the Tools menu:

```python
tools.add_command(label="Dataset Manager", command=self.open_dataset_manager)
```

## 8) Make AI Assistant references clickable
Wherever the assistant currently does:

```python
self.ai_output.insert("end", result)
```

replace it with:

```python
self.insert_assistant_text_with_links(self.ai_output, result)
```

If your widget has a different name, use that widget instead.

## 9) Stop AI Assistant from silently switching translations
In the assistant call path, make sure the selected translation is passed through, e.g.:

```python
translation = self.translation_var.get().strip().lower()
result = self.study_assistant.answer_question(question, translation=translation)
```

and in `study_assistant.py`, every DB query should honor that `translation` argument.
