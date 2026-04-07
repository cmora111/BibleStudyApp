
# Dataset Manager patch snippets for app/ui/main_window.py

from app.engines.dataset_manager import DatasetManager

# In __init__:
# self.dataset_manager = DatasetManager(Path.cwd())

# Optional notebook tab wiring:
# self.datasets_tab = ttk.Frame(self.right_notebook, width=360)
# self.right_notebook.add(self.datasets_tab, text="Datasets")
# self.build_datasets_tab(self.datasets_tab)

def build_datasets_tab(self, parent: ttk.Frame) -> None:
    frame = ttk.LabelFrame(parent, text="Dataset Manager")
    frame.pack(fill="both", expand=True, padx=6, pady=6)

    top = ttk.Frame(frame)
    top.pack(fill="x", padx=6, pady=6)

    ttk.Button(top, text="Refresh", command=self.refresh_datasets_panel).pack(side="left")
    ttk.Button(top, text="Check Disk", command=self.show_dataset_disk_status).pack(side="left", padx=(6, 0))
    ttk.Button(top, text="Register Local File", command=self.register_dataset_local_file).pack(side="left", padx=(6, 0))

    self.datasets_tree = ttk.Treeview(
        frame,
        columns=("category", "exists", "size_mb", "path"),
        show="headings",
        height=12,
    )
    self.datasets_tree.heading("category", text="Category")
    self.datasets_tree.heading("exists", text="Installed")
    self.datasets_tree.heading("size_mb", text="Size MB")
    self.datasets_tree.heading("path", text="Path")
    self.datasets_tree.column("category", width=120, anchor="w")
    self.datasets_tree.column("exists", width=80, anchor="center")
    self.datasets_tree.column("size_mb", width=80, anchor="e")
    self.datasets_tree.column("path", width=420, anchor="w")
    self.datasets_tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    self.datasets_status = tk.Text(frame, wrap="word", height=10)
    self.datasets_status.pack(fill="both", expand=False, padx=6, pady=(0, 6))

    self.refresh_datasets_panel()

def refresh_datasets_panel(self) -> None:
    for item in self.datasets_tree.get_children():
        self.datasets_tree.delete(item)

    rows = self.dataset_manager.installed_items()
    for row in rows:
        self.datasets_tree.insert(
            "",
            "end",
            iid=row["key"],
            values=(row["category"], "Yes" if row["exists"] else "No", row["size_mb"], row["path"]),
            text=row["label"],
        )

    self.datasets_status.delete("1.0", "end")
    self.datasets_status.insert("end", "Dataset catalog refreshed.\n")
    for row in rows:
        self.datasets_status.insert(
            "end",
            f"- {row['label']}: {'installed' if row['exists'] else 'missing'} ({row['size_mb']} MB)\n",
        )

def show_dataset_disk_status(self) -> None:
    disk = self.dataset_manager.free_disk_space()
    self.datasets_status.delete("1.0", "end")
    self.datasets_status.insert("end", f"Path: {disk['path']}\n")
    self.datasets_status.insert("end", f"Total GB: {disk['total_gb']}\n")
    self.datasets_status.insert("end", f"Free GB: {disk['free_gb']}\n")

def register_dataset_local_file(self) -> None:
    selected = self.datasets_tree.selection()
    if not selected:
        messagebox.showinfo("Dataset Manager", "Select a dataset row first.")
        return

    dataset_key = selected[0]
    local_file = filedialog.askopenfilename(title="Select local dataset file")
    if not local_file:
        return

    try:
        info = self.dataset_manager.register_local_file(dataset_key, local_file, copy_into_target=True)
    except Exception as exc:
        messagebox.showerror("Dataset Manager", f"Could not register dataset:\n\n{exc}")
        return

    self.refresh_datasets_panel()
    self.datasets_status.insert("end", f"\nRegistered dataset: {dataset_key}\n")
