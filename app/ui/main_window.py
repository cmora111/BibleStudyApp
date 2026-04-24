from __future__ import annotations

import re
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
from pathlib import Path
import webbrowser
import threading
import itertools
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy

from app.core.bible_db import BibleDB
from app.core.config import DB_FILE
from app.core.importers import parse_bible_file, parse_bible_folder, parse_strongs_file
from app.core.utils import pretty_ref
from app.engines.commentary import CommentaryEngine
from app.engines.knowledge_graph import KnowledgeGraphEngine
from app.engines.semantic_search import SemanticSearchEngine
from app.engines.strongs_engine import StrongsWordStudyEngine
from app.engines.study_assistant import AIBibleStudyAssistant
from app.engines.topic_engine import TopicEngine
from app.engines.timeline_engine import BibleTimelineEngine
from app.engines.map_engine import BibleMapEngine
from app.engines.dataset_manager import DatasetManager
from app.ui.dataset_import_wizard import DatasetImportWizard
from app.ui.setup_wizard import SetupWizard
from app.engines.event_graph_bridge import EventGraphBridge

try:
    from app.engines.cross_reference_engine import CrossReferenceEngine
except Exception:
    CrossReferenceEngine = None


class UltimateBibleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ultimate Bible App")
        self.root.geometry("1260x820")

        self.db = BibleDB()
        self.topic_engine = TopicEngine()
        self.commentary_engine = CommentaryEngine()
        self.graph_engine = KnowledgeGraphEngine()

        translations = self.db.translations() or ["kjv"]
        self.translation_var = tk.StringVar(value=translations[0])
        self.book_var = tk.StringVar(value="romans")
        self.chapter_var = tk.IntVar(value=8)
        self.verse_var = tk.IntVar(value=28)
        self.status_var = tk.StringVar(value="Ready")

        self.strongs_query_var = tk.StringVar(value="G26")
        self.import_translation_var = tk.StringVar(value="")
        self.import_format_var = tk.StringVar(value="auto")
        self.lexicon_format_var = tk.StringVar(value="auto")

        self._semantic_preview_stack = []
        self._semantic_preview_collapsed = set()
        self.semantic_engine = None
        self.strongs_engine = None
        self.study_assistant = None
        self.crossref_engine = CrossReferenceEngine() if CrossReferenceEngine else None
        self.timeline_engine = BibleTimelineEngine("data/timeline_events.csv")
        self.map_engine = BibleMapEngine()
        self.dataset_manager = DatasetManager(Path.cwd())
        self.event_graph_bridge = EventGraphBridge("data/timeline_events.csv")

        self._map_cache = {}
        self._last_focused_event_id = None
        self._timeline_select_after_id = None
        self._graph_nav_menu = None
        self._semantic_search_counter = itertools.count(1)
        self._active_semantic_search_token = 0
        self._strongs_result_cache = {}
        self._strongs_tooltip = None
        self._strongs_popup = None
        self._map_server_started = False
        self.build_ui()
        self.root.after(100, lambda: self.display_current_verse(skip_heavy_panels=True))

    def build_ui(self) -> None:
        self.build_menu()
        self.main_panes = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_panes.pack(fill="both", expand=True)

        left = ttk.Frame(self.main_panes, width=260)
        center = ttk.Frame(self.main_panes, width=620)
        right = ttk.Frame(self.main_panes, width=360)

        self.main_panes.add(left, weight=1)
        self.main_panes.add(center, weight=3)
        self.main_panes.add(right, weight=1)

        self.build_left_panel(left)
        self.build_center_panel(center)
        self.build_right_panel(right)

        ttk.Label(self.root, textvariable=self.status_var, anchor="w").pack(fill="x", padx=6, pady=4)

        self.root.update_idletasks()
        try:
            self.main_panes.sashpos(0, 260)
            self.main_panes.sashpos(1, 880)
        except Exception:
            pass

    def build_menu(self) -> None:
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        tools_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        menu.add_cascade(label="Tools", menu=tools_menu)
        file_menu.add_command(label="Import Bible File", command=self.import_bible)
        file_menu.add_command(label="Import Bible Folder", command=self.import_bible_folder)
        file_menu.add_command(label="Import Strong's File", command=self.import_strongs_file)
        file_menu.add_separator()
        file_menu.add_command(label="Rebuild Semantic Index", command=self.rebuild_semantic_index)
        file_menu.add_separator()
        file_menu.add_command(label="Open Dataset Import Wizard", command=self.open_dataset_import_wizard)
        file_menu.add_command(label="Open Setup Wizard", command=self.open_setup_wizard)
        file_menu.add_command(label="Exit", command=self.root.destroy)
        tools_menu.add_command(label="Semantic Search", command=self.run_semantic_search)
        tools_menu.add_command(label="Generate Study Guide", command=self.run_ai_assistant)
        tools_menu.add_command(label="Strong's Word Study", command=self.run_strongs_lookup)
        tools_menu.add_command(label="Generate Commentary", command=self.generate_commentary)
        tools_menu.add_command(label="Export Knowledge Graph", command=self.export_graph)

    def rebuild_semantic_index(self) -> None:
        translation = (self.translation_var.get() or "").strip().lower()
        self.semantic_engine = None
        self.study_assistant = None
        self.status_var.set(f"Semantic engine reset for {translation.upper()}")

        if hasattr(self, "search_results"):
            try:
                self.search_results.delete("1.0", "end")
                self.search_results.insert("end", f"Semantic engine will rebuild on next search for {translation.upper()}\n")
            except Exception:
                pass

    def _ensure_semantic_engine(self):
        translation = (self.translation_var.get() or "").strip().lower()
        if self.semantic_engine is None:
            self.status_var.set(f"Loading semantic engine for {translation.upper()}...")
            self.semantic_engine = SemanticSearchEngine(self.db, translation=translation)
        return self.semantic_engine

    def _clear_semantic_preview_stack(self):
        self._semantic_preview_stack = []
        self._semantic_preview_collapsed = set()
        self._render_semantic_preview_stack()
        self.status_var.set("Semantic preview stack cleared")

    def _remove_semantic_preview_at(self, index: int):
        try:
            if 0 <= index < len(self._semantic_preview_stack):
                removed = self._semantic_preview_stack.pop(index)

                key = (
                    removed.translation.lower(),
                    removed.book.lower(),
                    int(removed.chapter),
                    int(removed.verse),
                )
                self._semantic_preview_collapsed.discard(key)

                self._render_semantic_preview_stack()
                self.status_var.set(
                    f"Removed preview {pretty_ref(removed.book, removed.chapter, removed.verse)}"
                )
        except Exception as exc:
            try:
                messagebox.showerror("Semantic Preview", f"Could not remove preview:\n\n{exc}")
            except Exception:
                pass

    def _ensure_strongs_engine(self):
        translation = (self.translation_var.get() or "").strip().lower()
        if self.strongs_engine is None:
            self.status_var.set(f"Loading Strong's engine for {translation.upper()}...")
            self.strongs_engine = StrongsWordStudyEngine(self.db, translation=translation)
        return self.strongs_engine

    def _ensure_study_assistant(self):
        if self.study_assistant is None:
            semantic_engine = self._ensure_semantic_engine()
            strongs_engine = self._ensure_strongs_engine()
            self.study_assistant = AIBibleStudyAssistant(semantic_engine, strongs_engine)
        return self.study_assistant

    def on_translation_change(self) -> None:
        translation = (self.translation_var.get() or "").strip().lower()

        try:
            self.strongs_query_var.set(self.strongs_query_var.get())
        except Exception:
            pass

        self._strongs_result_cache.clear()
        self.semantic_engine = None
        self.strongs_engine = None
        self.study_assistant = None
        self._semantic_preview_stack = []

        try:
            self.display_current_verse(skip_heavy_panels=True)
        except Exception as exc:
            try:
                messagebox.showerror("Translation", f"Could not refresh verse:\n\n{exc}")
            except Exception:
                pass
            return

        self.status_var.set(f"Translation changed to {translation.upper()}")

    def prettify_reference_label(self, text: str) -> str:
        value = (text or "").strip()

        mapping = {
            "genesis": "Genesis", "exodus": "Exodus", "leviticus": "Leviticus", "numbers": "Numbers",
            "deuteronomy": "Deuteronomy", "joshua": "Joshua", "judges": "Judges", "ruth": "Ruth",
            "1samuel": "1 Samuel", "2samuel": "2 Samuel", "1kings": "1 Kings", "2kings": "2 Kings",
            "1chronicles": "1 Chronicles", "2chronicles": "2 Chronicles", "ezra": "Ezra", "nehemiah": "Nehemiah",
            "esther": "Esther", "job": "Job", "psalms": "Psalms", "proverbs": "Proverbs",
            "ecclesiastes": "Ecclesiastes", "songofsolomon": "Song of Solomon", "isaiah": "Isaiah",
            "jeremiah": "Jeremiah", "lamentations": "Lamentations", "ezekiel": "Ezekiel", "daniel": "Daniel",
            "hosea": "Hosea", "joel": "Joel", "amos": "Amos", "obadiah": "Obadiah", "jonah": "Jonah",
            "micah": "Micah", "nahum": "Nahum", "habakkuk": "Habakkuk", "zephaniah": "Zephaniah",
            "haggai": "Haggai", "zechariah": "Zechariah", "malachi": "Malachi", "matthew": "Matthew",
            "mark": "Mark", "luke": "Luke", "john": "John", "acts": "Acts", "romans": "Romans",
            "1corinthians": "1 Corinthians", "2corinthians": "2 Corinthians", "galatians": "Galatians",
            "ephesians": "Ephesians", "philippians": "Philippians", "colossians": "Colossians",
            "1thessalonians": "1 Thessalonians", "2thessalonians": "2 Thessalonians", "1timothy": "1 Timothy",
            "2timothy": "2 Timothy", "titus": "Titus", "philemon": "Philemon", "hebrews": "Hebrews",
            "james": "James", "1peter": "1 Peter", "2peter": "2 Peter", "1john": "1 John",
            "2john": "2 John", "3john": "3 John", "jude": "Jude", "revelation": "Revelation",
            "ijohn": "1 John", "iijohn": "2 John", "iiijohn": "3 John",
            "ipeter": "1 Peter", "iipeter": "2 Peter",
            "isamuel": "1 Samuel", "iisamuel": "2 Samuel",
            "ikings": "1 Kings", "iikings": "2 Kings",
            "ichronicles": "1 Chronicles", "iichronicles": "2 Chronicles",
        }

        m = re.match(r'^([1-3]|i{1,3})\s*([A-Za-z]+)\s+(\d+:\d+(?:-\d+)?)$', value, re.IGNORECASE)
        if m:
            prefix = m.group(1).lower()
            book = m.group(2).lower()
            ref = m.group(3)
            numeral_map = {"i": "1", "ii": "2", "iii": "3"}
            prefix_num = numeral_map.get(prefix, prefix)
            key = f"{prefix_num}{book}"
            pretty_book = mapping.get(key, f"{prefix_num} {book.title()}")
            return f"{pretty_book} {ref}"

        m2 = re.match(r'^([A-Za-z0-9]+)\s+(\d+:\d+(?:-\d+)?)$', value)
        if m2:
            key = m2.group(1).lower()
            ref = m2.group(2)
            if key in mapping:
                return f"{mapping[key]} {ref}"

        return value

    def build_left_panel(self, parent: ttk.Frame) -> None:
        nav = ttk.LabelFrame(parent, text="Navigation / Search")
        nav.pack(fill="x", padx=8, pady=8)
        ttk.Label(nav, text="Translation").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.translation_combo = ttk.Combobox(nav, textvariable=self.translation_var, values=self.db.translations() or ["kjv"], state="readonly")
        self.translation_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self.translation_combo.bind("<<ComboboxSelected>>", lambda e: self.on_translation_change())
        ttk.Label(nav, text="Quick Ref").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(nav, textvariable=self.book_var).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(nav, text="Prev Verse", command=self.prev_verse).grid(row=2, column=0, sticky="ew", padx=4, pady=6)
        ttk.Button(nav, text="Next Verse", command=self.next_verse).grid(row=2, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(nav, text="Generate Study Guide", command=self.run_ai_assistant).grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        nav.columnconfigure(1, weight=1)

        search_box = ttk.LabelFrame(parent, text="Semantic Search")
        search_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.search_entry = ttk.Entry(search_box)
        self.search_entry.pack(fill="x", padx=6, pady=6)
        self.search_entry.insert(0, "love")
        ttk.Button(search_box, text="Search", command=self.run_semantic_search).pack(fill="x", padx=6, pady=4)
        self.search_results = tk.Text(search_box, wrap="word", height=18, cursor="xterm")
        self.search_results.pack(fill="both", expand=True, padx=6, pady=6)

    def build_center_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Bible Reader")
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        topbar = ttk.Frame(frame)
        topbar.pack(fill="x", padx=6, pady=(6, 4))
        ttk.Label(topbar, text="Book").pack(side="left", padx=(0, 4))
        ttk.Entry(topbar, textvariable=self.book_var, width=16).pack(side="left", padx=(0, 8))
        ttk.Label(topbar, text="Chapter").pack(side="left", padx=(0, 4))
        ttk.Entry(topbar, textvariable=self.chapter_var, width=6).pack(side="left", padx=(0, 8))
        ttk.Label(topbar, text="Verse").pack(side="left", padx=(0, 4))
        ttk.Entry(topbar, textvariable=self.verse_var, width=6).pack(side="left", padx=(0, 8))
        ttk.Button(topbar, text="Go", command=self.display_current_verse).pack(side="left", padx=(0, 6))
        ttk.Button(topbar, text="Read Chapter", command=self.read_current_chapter).pack(side="left")

        self.reader = tk.Text(frame, wrap="word", font=("TkDefaultFont", 11))
        self.reader.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(frame, text="Tip: blue underlined words have Strong's links. Click one to open a word study.").pack(anchor="w", padx=6, pady=(0, 6))

    def build_right_panel(self, parent: ttk.Frame) -> None:
        self.right_notebook = ttk.Notebook(parent, width=320)
        self.right_notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.study_tab = ttk.Frame(self.right_notebook, width=360)
        self.crossrefs_tab = ttk.Frame(self.right_notebook, width=360)
        self.compare_tab = ttk.Frame(self.right_notebook, width=360)
        self.commentary_tab = ttk.Frame(self.right_notebook, width=360)
        self.graph_tab = ttk.Frame(self.right_notebook, width=360)
        self.import_tab = ttk.Frame(self.right_notebook, width=360)
        self.timeline_tab = ttk.Frame(self.right_notebook, width=360)
        self.datasets_tab = ttk.Frame(self.right_notebook, width=360)

        self.right_notebook.add(self.study_tab, text="Study Guide")
        self.right_notebook.add(self.crossrefs_tab, text="Cross Refs")
        self.right_notebook.add(self.compare_tab, text="Compare")
        self.right_notebook.add(self.commentary_tab, text="Commentary/Strong's")
        self.right_notebook.add(self.graph_tab, text="Knowledge Graph")
        self.right_notebook.add(self.timeline_tab, text="Timeline / Map")
        self.right_notebook.add(self.datasets_tab, text="Datasets")
        self.right_notebook.add(self.import_tab, text="Import")

        self.build_study_tab(self.study_tab)
        self.build_crossrefs_tab(self.crossrefs_tab)
        self.build_compare_tab(self.compare_tab)
        self.build_commentary_tab(self.commentary_tab)
        self.build_graph_tab(self.graph_tab)
        self.build_timeline_tab(self.timeline_tab)
        self.build_datasets_tab(self.datasets_tab)
        self.build_import_tab(self.import_tab)

        self.right_notebook.bind("<<NotebookTabChanged>>", self._on_right_tab_changed)

    def _on_right_tab_changed(self, event=None):
        try:
            current = self.right_notebook.select()
            tab_text = self.right_notebook.tab(current, "text")
        except Exception:
            return

        if tab_text == "Timeline / Map" and not getattr(self, "_timeline_loaded", False):
            self._timeline_loaded = True
            try:
                self._ensure_map_callback_server()
            except Exception:
                pass
            try:
                self.refresh_timeline_panel()
            except Exception as exc:
                try:
                    self.timeline_details.delete("1.0", "end")
                    self.timeline_details.insert("end", f"Could not load timeline panel:\n{exc}")
                except Exception:
                    pass
            return

        if tab_text == "Commentary/Strong's":
            try:
                if getattr(self, "_semantic_preview_stack", []):
                    self._render_semantic_preview_stack()
                else:
                    self._populate_commentary_tab_for_current_verse()
            except Exception as exc:
                try:
                    self.commentary_output.delete("1.0", "end")
                    self.commentary_output.insert(
                        "end",
                        f"Could not prepare Commentary/Strong's tab:\n{exc}"
                    )
                except Exception:
                    pass

    def _populate_commentary_tab_for_current_verse(self):
        if not hasattr(self, "commentary_output"):
            return

        verse = self.current_verse()
        self.commentary_output.delete("1.0", "end")

        if verse is None:
            self.commentary_output.insert("end", "No current verse selected.\n")
            return

        self.commentary_output.insert(
            "end",
            f"Current verse: {pretty_ref(verse.book, verse.chapter, verse.verse)} [{verse.translation.upper()}]\n\n",
        )

        links = self.build_top_clickable_strongs_list(
            verse.book, verse.chapter, verse.verse, verse.translation
        )

        if links:
            self.commentary_output.tag_configure(
                "section_header",
                font=("TkDefaultFont", 10, "bold")
            )
            self.commentary_output.insert(
                "end",
                "Strong's links in this verse:\n",
                ("section_header",)
            )

            for idx, (word, code) in enumerate(links[:20], start=1):
                code = str(code).strip().upper()
                if code.isdigit():
                    code = f"G{code}"

                self.commentary_output.insert("end", f"{idx}. {word} (", ())
                start = self.commentary_output.index("end")
                self.commentary_output.insert("end", code, ())
                end = self.commentary_output.index("end")

                tag = f"commentary_current_{idx}_{code}"
                self.commentary_output.tag_add(tag, start, end)
                self._bind_commentary_strongs_tag(tag, code)

                self.commentary_output.insert("end", ")\n", ())

            self.commentary_output.insert(
                "end",
                "\nUse Strong's Lookup or Commentary to load detailed content.\n",
            )
        else:
            self.commentary_output.insert(
                "end",
                "No Strong's links are available for the current verse/translation.\n",
            )

    def build_study_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Generate Study Guide")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.question_entry = ttk.Entry(frame)
        self.question_entry.pack(fill="x", padx=6, pady=6)
        self.question_entry.insert(0, "What does this verse teach?")
        ttk.Button(frame, text="Generate Study Guide", command=self.run_ai_assistant).pack(fill="x", padx=6, pady=4)
        self.study_questions_frame = ttk.Frame(frame)
        self.study_questions_frame.pack(fill="x", padx=6, pady=6)
        self.assistant_output = tk.Text(frame, wrap="word", height=16)
        self.assistant_output.pack(fill="both", expand=True, padx=6, pady=6)

    def build_crossrefs_tab(self, parent: ttk.Frame) -> None:
        outer = ttk.LabelFrame(parent, text="Cross References")
        outer.pack(fill="both", expand=True, padx=6, pady=6)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.crossrefs_container = ttk.Frame(canvas)
        self.crossrefs_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.crossrefs_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        scrollbar.pack(side="right", fill="y", padx=(0, 6), pady=6)

    def build_compare_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Verse Compare")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.compare_output = tk.Text(frame, wrap="word", height=20)
        self.compare_output.pack(fill="both", expand=True, padx=6, pady=6)

    def build_graph_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Knowledge Graph View")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", padx=6, pady=6)

        ttk.Button(controls, text="Show Selected Timeline Event", command=self.show_selected_timeline_in_graph_view).pack(side="left")
        ttk.Button(controls, text="Export Full Graph", command=self.export_graph).pack(side="left", padx=(6, 0))

        self.graph_event_label_var = tk.StringVar(value="No event selected")
        ttk.Label(frame, textvariable=self.graph_event_label_var).pack(anchor="w", padx=6, pady=(0, 6))

        self.graph_output = tk.Text(frame, wrap="word", height=18)
        self.graph_output.pack(fill="both", expand=True, padx=6, pady=6)

    def build_timeline_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Bible Timeline + Map Explorer")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", padx=6, pady=6)

        self.timeline_filter_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=self.timeline_filter_var).pack(side="left", fill="x", expand=True)
        ttk.Button(controls, text="Filter", command=self.refresh_timeline_panel).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Current Book", command=self.filter_timeline_current_book).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Open Full Map", command=self.open_timeline_map).pack(side="left", padx=(6, 0))

        era_bar = ttk.Frame(frame)
        era_bar.pack(fill="x", padx=6, pady=(0, 6))
        for label, era in [
            ("All", ""),
            ("Primeval", "Primeval"),
            ("Patriarchs", "Patriarchs"),
            ("Exodus", "Exodus/Wilderness"),
            ("Kingdom", "United Kingdom"),
            ("Divided", "Divided Kingdom"),
            ("Exile", "Exile/Return"),
            ("Christ", "Life of Christ"),
            ("Acts", "Acts/Apostolic"),
        ]:
            ttk.Button(era_bar, text=label, command=lambda value=era: self.filter_timeline_era(value)).pack(side="left", padx=(0, 4))

        split = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        split.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(split)
        right = ttk.Frame(split)
        split.add(left, weight=4)
        split.add(right, weight=2)

        self.timeline_list = tk.Listbox(left, height=16)
        self.timeline_list.pack(fill="both", expand=True, padx=0, pady=(0, 6))
        self.timeline_list.bind("<<ListboxSelect>>", lambda e: self.on_timeline_select())

        details = ttk.LabelFrame(left, text="Event Details")
        details.pack(fill="both", expand=True)
        self.timeline_details = tk.Text(details, wrap="word", height=12)
        self.timeline_details.pack(fill="both", expand=True, padx=6, pady=6)

        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Open", command=self.open_selected_timeline_event_in_reader).pack(side="left")

        self.timeline_action_menu = tk.Menu(self.root, tearoff=0)
        self.timeline_action_menu.add_command(label="Search Event", command=self.search_selected_timeline_event)
        self.timeline_action_menu.add_command(label="Show Graph Links", command=self.show_selected_timeline_graph_links)

        def _open_timeline_action_menu(event=None):
            try:
                self.timeline_action_menu.tk_popup(event.x_root, event.y_root)
            finally:
                try:
                    self.timeline_action_menu.grab_release()
                except Exception:
                    pass

        explore_btn = ttk.Button(buttons, text="Explore ▼")
        explore_btn.pack(side="left", padx=(6, 0))
        explore_btn.bind("<Button-1>", _open_timeline_action_menu)

        map_box = ttk.LabelFrame(right, text="Map Explorer")
        map_box.pack(fill="both", expand=True)

        self.map_focus_label_var = tk.StringVar(value="No map focus selected")
        ttk.Label(map_box, textvariable=self.map_focus_label_var, wraplength=280, justify="left").pack(anchor="w", padx=6, pady=(6, 4))

        self.map_preview_status_var = tk.StringVar(value="Maps open in your browser. Select an event, then use Selected Event Map only when needed.")
        ttk.Label(map_box, textvariable=self.map_preview_status_var, wraplength=280, justify="left").pack(anchor="w", padx=6, pady=(0, 6))

        self.map_meta_output = tk.Text(map_box, wrap="word", height=18)
        self.map_meta_output.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        map_btns = ttk.Frame(map_box)
        map_btns.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(map_btns, text="Selected Event Map", command=self.open_selected_timeline_location_on_map).pack(side="left")
        ttk.Button(map_btns, text="Full Timeline Map", command=self.open_timeline_map).pack(side="left", padx=(6, 0))

        self._timeline_events_cache = []
        self._timeline_loaded = False
        self.timeline_list.insert("end", "Timeline loads when opened.")

    def build_commentary_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Commentary / Strong's")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        top = ttk.Frame(frame)
        top.pack(fill="x", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.strongs_query_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(top, text="Strong's Lookup", command=self.run_strongs_lookup).pack(side="left")
        ttk.Button(top, text="Commentary", command=self.generate_commentary).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Clear Semantic Previews", command=self._clear_semantic_preview_stack).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Clear Semantic Previews",
                   command=self._clear_semantic_preview_stack).pack(side="left",
                                                                    padx=(6, 0))
        self.commentary_output = tk.Text(frame, wrap="word", height=20)
        self.commentary_output.pack(fill="both", expand=True, padx=6, pady=6)


    def refresh_after_dataset_change(self):
        try:
            self.crossref_engine = CrossReferenceEngine() if CrossReferenceEngine else None
        except Exception:
            self.crossref_engine = None
        try:
            if self.crossref_engine and hasattr(self.crossref_engine, "reload"):
                self.crossref_engine.reload()
        except Exception:
            pass
        try:
            self.refresh_crossrefs_panel()
        except Exception:
            pass
        try:
            self.refresh_datasets_panel()
        except Exception:
            pass

    def _safe_open_strongs_code(self, code: str, event=None):
        code = str(code or "").strip().upper()
        if not code:
            return
        if code.isdigit():
            code = f"G{code}"

        cached = self._strongs_result_cache.get(code)
        if cached is not None:
            self.show_strongs_result_popup(code, cached)
            return

        try:
            strongs_engine = self._ensure_strongs_engine()
            result = strongs_engine.study_code(code)
            self._strongs_result_cache[code] = result
        except Exception as exc:
            try:
                messagebox.showerror("Strong's Lookup", f"Could not open Strong's code {code}: {exc}")
            except Exception:
                pass
            return

        self.show_strongs_result_popup(code, result)

    def show_strongs_result_popup(self, code: str, result):
        win = tk.Toplevel(self.root)
        win.title(f"Strong's {code}")
        win.geometry("760x520")

        txt = tk.Text(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)

        lines = [f"Strong's {code}", ""]

        entry = getattr(result, "entry", None)
        if entry:
            lines.append(f"Lemma: {getattr(entry, 'lemma', '')}")
            lines.append(f"Transliteration: {getattr(entry, 'transliteration', '')}")
            lines.append(f"Language: {getattr(entry, 'language', '')}")
            lines.append(f"Gloss: {getattr(entry, 'gloss', '')}")
            lines.append(f"Definition: {getattr(entry, 'definition', '')}")
            lines.append("")

        linked_codes = getattr(result, "linked_codes", None)
        if linked_codes:
            lines.append("Linked Codes:")
            lines.append(", ".join(str(x) for x in linked_codes))
            lines.append("")

        occurrences = getattr(result, "occurrences", None)
        if occurrences:
            lines.append("Occurrences:")
            for item in occurrences[:20]:
                lines.append(f"- {item}")
            lines.append("")

        verse_hits = getattr(result, "verse_hits", None)
        if verse_hits:
            lines.append("Verse Hits:")
            for item in verse_hits[:20]:
                lines.append(f"- {item}")
            lines.append("")

        if len(lines) <= 2:
            lines.append(str(result))

        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")

    def _bind_reader_strongs_tag(self, tag: str, code: str):
        code = str(code or "").strip().upper()
        if code.isdigit():
            code = f"G{code}"

        self.reader.tag_configure(tag, foreground="blue", underline=1)
        self.reader.tag_bind(
            tag,
            "<Button-1>",
            lambda e, c=code: self._safe_open_strongs_code(str(c), event=e)
        )
        self.reader.tag_bind(
            tag,
            "<Button-3>",
            lambda e, c=code: self._show_strongs_context_menu(e, str(c))
        )
        self.reader.tag_bind(
            tag,
            "<Enter>",
            lambda e, t=tag, c=code: (
                self.reader.config(cursor="hand2"),
                self.reader.tag_configure(t, foreground="blue", underline=1, background="#eef6ff"),
                self._show_strongs_tooltip(e, str(c))
            )
        )
        self.reader.tag_bind(
            tag,
            "<Leave>",
            lambda e, t=tag: (
                self.reader.config(cursor="xterm"),
                self.reader.tag_configure(t, foreground="blue", underline=1, background=""),
                self._hide_strongs_tooltip()
            )
        )

    def _ensure_map_callback_server(self):
        if getattr(self, "_map_server_started", False):
            return
        try:
            self.start_map_callback_server()
            self._map_server_started = True
        except Exception as exc:
            print(f"Could not start map callback server: {exc}")

    def _hide_semantic_result_tooltip(self, event=None):
        tip = getattr(self, "_semantic_result_tooltip", None)
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
            self._semantic_result_tooltip = None

    def _show_semantic_result_tooltip(self, event, hit):
        verse_obj = getattr(hit, "verse", None)
        if verse_obj is None:
            return

        self._hide_semantic_result_tooltip()

        try:
            ref = pretty_ref(verse_obj.book, verse_obj.chapter, verse_obj.verse)
            text = self.sanitize_display_text(verse_obj.text or "")
            if len(text) > 260:
                text = text[:257].rstrip() + "..."

            tip = tk.Toplevel(self.root)
            tip.transient(self.root)
            tip.resizable(False, False)

            x = getattr(event, "x_root", self.root.winfo_rootx() + 20) + 12
            y = getattr(event, "y_root", self.root.winfo_rooty() + 20) + 12
            tip.geometry(f"+{x}+{y}")

            frame = ttk.Frame(tip, padding=8)
            frame.pack(fill="both", expand=True)

            title = ttk.Label(
                frame,
                text=f"{ref} [{verse_obj.translation.upper()}]",
                font=("TkDefaultFont", 10, "bold"),
                justify="left",
            )
            title.pack(anchor="w")

            body = tk.Label(
                frame,
                text=text,
                justify="left",
                anchor="nw",
                bg="#fff8dc",
                relief="solid",
                borderwidth=1,
                padx=8,
                pady=6,
                wraplength=420,
            )
            body.pack(fill="both", expand=True, pady=(6, 0))

            self._semantic_result_tooltip = tip
            tip.lift()
        except Exception:
            self._semantic_result_tooltip = None

    def _hide_strongs_tooltip(self, event=None):
        tip = getattr(self, "_strongs_tooltip", None)
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
            self._strongs_tooltip = None

    def _show_strongs_tooltip(self, event, code: str):
        code = str(code or "").strip().upper()
        if not code:
            return
        if code.isdigit():
            code = f"G{code}"

        self._hide_strongs_tooltip()

        try:
            tip = tk.Toplevel(self.root)
            tip.wm_overrideredirect(True)
            x = getattr(event, "x_root", self.root.winfo_rootx() + 20) + 12
            y = getattr(event, "y_root", self.root.winfo_rooty() + 20) + 12
            tip.wm_geometry(f"+{x}+{y}")

            label = tk.Label(
                tip,
                text=f"Strong's {code}\nClick for full study",
                justify="left",
                bg="#fff8dc",
                relief="solid",
                borderwidth=1,
                padx=6,
                pady=4,
                wraplength=240,
            )
            label.pack()

            self._strongs_tooltip = tip
            tip.lift()
        except Exception:
            self._strongs_tooltip = None

    def copy_text_to_clipboard(self, text: str):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            self.status_var.set("Copied to clipboard")
        except Exception:
            pass

    def _show_strongs_context_menu(self, event, code: str):
        code = str(code or "").strip().upper()
        if code.isdigit():
            code = f"G{code}"

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Open {code}", command=lambda c=code: self._safe_open_strongs_code(c))
        menu.add_command(label=f"Copy {code}", command=lambda c=code: self.copy_text_to_clipboard(c))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def open_dataset_import_wizard(self):
        try:
            DatasetImportWizard(self.root, self.dataset_manager, on_complete=self.refresh_after_dataset_change)
        except Exception as exc:
            messagebox.showerror("Dataset Import Wizard", f"Could not open dataset import wizard:\n\n{exc}")

    def open_setup_wizard(self):
        try:
            SetupWizard(self.root, self.dataset_manager, on_complete=self.refresh_after_dataset_change)
        except Exception as exc:
            messagebox.showerror("Setup Wizard", f"Could not open setup wizard:\n\n{exc}")

    def build_datasets_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Dataset Manager")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        top = ttk.Frame(frame)
        top.pack(fill="x", padx=6, pady=6)

        ttk.Button(top, text="Refresh", command=self.refresh_datasets_panel).pack(side="left")
        ttk.Button(top, text="Check Disk", command=self.show_dataset_disk_status).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Import Wizard", command=self.open_dataset_import_wizard).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Setup Wizard", command=self.open_setup_wizard).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Register Local File", command=self.register_dataset_local_file).pack(side="left", padx=(6, 0))

        self.datasets_tree = ttk.Treeview(
            frame,
            columns=("label", "category", "installed", "size_mb", "path"),
            show="headings",
            height=12,
        )
        self.datasets_tree.heading("label", text="Label")
        self.datasets_tree.heading("category", text="Category")
        self.datasets_tree.heading("installed", text="Installed")
        self.datasets_tree.heading("size_mb", text="Size MB")
        self.datasets_tree.heading("path", text="Path")
        self.datasets_tree.column("label", width=180, anchor="w")
        self.datasets_tree.column("category", width=110, anchor="w")
        self.datasets_tree.column("installed", width=80, anchor="center")
        self.datasets_tree.column("size_mb", width=80, anchor="e")
        self.datasets_tree.column("path", width=320, anchor="w")
        self.datasets_tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.datasets_tree.bind("<<TreeviewSelect>>", lambda e: self.show_selected_dataset_details())

        self.datasets_status = tk.Text(frame, wrap="word", height=10)
        self.datasets_status.pack(fill="both", expand=False, padx=6, pady=(0, 6))

        self.refresh_datasets_panel()

    def refresh_datasets_panel(self) -> None:
        if not hasattr(self, "datasets_tree"):
            return

        for item in self.datasets_tree.get_children():
            self.datasets_tree.delete(item)

        rows = self.dataset_manager.installed_items()
        self._dataset_rows_by_key = {row["key"]: row for row in rows}

        for row in rows:
            self.datasets_tree.insert(
                "",
                "end",
                iid=row["key"],
                values=(
                    row["label"],
                    row["category"],
                    "Yes" if row["exists"] else "No",
                    row["size_mb"],
                    row["path"],
                ),
            )

        self.datasets_status.delete("1.0", "end")
        self.datasets_status.insert("end", "Dataset catalog refreshed.\n\n")
        for row in rows:
            self.datasets_status.insert(
                "end",
                f"- {row['label']}: {'installed' if row['exists'] else 'missing'} ({row['size_mb']} MB)\n",
            )

    def show_selected_dataset_details(self) -> None:
        if not hasattr(self, "datasets_tree"):
            return

        sel = self.datasets_tree.selection()
        if not sel:
            return

        key = sel[0]
        row = getattr(self, "_dataset_rows_by_key", {}).get(key)
        if not row:
            return

        item = self.dataset_manager.get_item(key)
        self.datasets_status.delete("1.0", "end")
        self.datasets_status.insert("end", f"{item.label}\n\n")
        self.datasets_status.insert("end", f"Key: {item.key}\n")
        self.datasets_status.insert("end", f"Category: {item.category}\n")
        self.datasets_status.insert("end", f"Installed: {'Yes' if row['exists'] else 'No'}\n")
        self.datasets_status.insert("end", f"Size MB: {row['size_mb']}\n")
        self.datasets_status.insert("end", f"Path: {row['path']}\n\n")
        self.datasets_status.insert("end", f"{item.description}\n")

    def show_dataset_disk_status(self) -> None:
        disk = self.dataset_manager.free_disk_space()
        self.datasets_status.delete("1.0", "end")
        self.datasets_status.insert("end", "Disk Status\n\n")
        self.datasets_status.insert("end", f"Path: {disk['path']}\n")
        self.datasets_status.insert("end", f"Total GB: {disk['total_gb']}\n")
        self.datasets_status.insert("end", f"Free GB: {disk['free_gb']}\n")

    def register_dataset_local_file(self) -> None:
        if not hasattr(self, "datasets_tree"):
            return

        sel = self.datasets_tree.selection()
        if not sel:
            messagebox.showinfo("Dataset Manager", "Select a dataset row first.")
            return

        key = sel[0]
        item = self.dataset_manager.get_item(key)
        local_file = filedialog.askopenfilename(title=f"Select local file for {item.label}")
        if not local_file:
            return

        try:
            self.dataset_manager.register_local_file(key, local_file, copy_into_target=True)
        except Exception as exc:
            messagebox.showerror("Dataset Manager", f"Could not register dataset:\n\n{exc}")
            return

        self.refresh_datasets_panel()
        self.datasets_status.insert("end", f"\nRegistered dataset for {item.label}.\n")

    def build_import_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Licensed Dataset Import")
        frame.pack(fill="x", padx=6, pady=6)
        ttk.Label(frame, text="Override translation").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(frame, textvariable=self.import_translation_var).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(frame, text="Bible format").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(frame, textvariable=self.import_format_var, values=["auto", "pipe", "csv", "jsonl"], state="readonly").grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(frame, text="Lexicon format").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(frame, textvariable=self.lexicon_format_var, values=["auto", "csv", "jsonl"], state="readonly").grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(frame, text="Import Bible File", command=self.import_bible).grid(row=3, column=0, sticky="ew", padx=4, pady=6)
        ttk.Button(frame, text="Import Bible Folder", command=self.import_bible_folder).grid(row=3, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(frame, text="Import Strong's File", command=self.import_strongs_file).grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        frame.columnconfigure(1, weight=1)

    def _connect_raw_db(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    def get_token_tags_for_verse(self, book: str, chapter: int, verse: int, translation: str):
        with self._connect_raw_db() as conn:
            cols = [row["name"] for row in conn.execute("PRAGMA table_info(verse_token_tags)").fetchall()]

            def pick(*names):
                for name in names:
                    if name in cols:
                        return name
                return None

            col_translation = pick("translation")
            col_book = pick("book")
            col_chapter = pick("chapter")
            col_verse = pick("verse")
            col_token = pick("token", "word", "surface", "token_text", "text")
            col_strongs = pick("strongs", "strongs_id", "code", "lemma_code")
            col_pos = pick("token_index", "position", "pos", "word_index", "token_pos")

            if not all([col_book, col_chapter, col_verse, col_token, col_strongs]):
                return []

            select_cols = [col_token, col_strongs]
            if col_pos:
                select_cols.append(col_pos)

            where = [f"{col_book}=?", f"{col_chapter}=?", f"{col_verse}=?"]
            params = [book, int(chapter), int(verse)]

            if col_translation:
                where.append(f"{col_translation}=?")
                params.append(translation)

            order_sql = f" ORDER BY {col_pos}" if col_pos else ""
            sql = f"""
                SELECT {", ".join(select_cols)}
                FROM verse_token_tags
                WHERE {' AND '.join(where)}
                {order_sql}
            """
            rows = conn.execute(sql, params).fetchall()

        result = []
        for row in rows:
            token = row[col_token]
            strongs = row[col_strongs]
            pos = row[col_pos] if col_pos else None
            if strongs and str(strongs).strip():
                result.append({
                    "token": str(token),
                    "strongs": str(strongs),
                    "position": pos,
                })
        return result

    def build_top_clickable_strongs_list(self, book: str, chapter: int, verse: int, translation: str):
        tags = self.get_token_tags_for_verse(book, chapter, verse, translation)
        clickable = []
        seen = set()
        for row in tags:
            token = row["token"].strip()
            strongs = row["strongs"].strip().upper()
            if not token or not strongs:
                continue
            if strongs[0] not in {"G", "H"} and strongs.isdigit():
                strongs = f"G{strongs}"
            key = (token, strongs)
            if key in seen:
                continue
            seen.add(key)
            clickable.append(key)
        return clickable

    def normalize_book_name(self, raw_book: str) -> str:
        raw = (raw_book or "").strip().lower()
        compact = raw.replace(" ", "").replace(".", "")

        mapping = {
            "genesis": "genesis",
            "gen": "genesis",
            "exodus": "exodus",
            "exo": "exodus",
            "leviticus": "leviticus",
            "lev": "leviticus",
            "numbers": "numbers",
            "num": "numbers",
            "deuteronomy": "deuteronomy",
            "deut": "deuteronomy",
            "joshua": "joshua",
            "josh": "joshua",
            "judges": "judges",
            "judg": "judges",
            "ruth": "ruth",
            "1samuel": "1samuel",
            "isamuel": "1samuel",
            "i samuel": "1samuel",
            "1 samuel": "1samuel",
            "2samuel": "2samuel",
            "iisamuel": "2samuel",
            "ii samuel": "2samuel",
            "2 samuel": "2samuel",
            "1kings": "1kings",
            "ikings": "1kings",
            "i kings": "1kings",
            "1 kings": "1kings",
            "2kings": "2kings",
            "iikings": "2kings",
            "ii kings": "2kings",
            "2 kings": "2kings",
            "1chronicles": "1chronicles",
            "ichronicles": "1chronicles",
            "i chronicles": "1chronicles",
            "1 chronicles": "1chronicles",
            "2chronicles": "2chronicles",
            "iichronicles": "2chronicles",
            "ii chronicles": "2chronicles",
            "2 chronicles": "2chronicles",
            "ezra": "ezra",
            "nehemiah": "nehemiah",
            "esther": "esther",
            "job": "job",
            "psalm": "psalms",
            "psalms": "psalms",
            "ps": "psalms",
            "proverbs": "proverbs",
            "prov": "proverbs",
            "ecclesiastes": "ecclesiastes",
            "songofsolomon": "songofsolomon",
            "song of solomon": "songofsolomon",
            "songofsongs": "songofsolomon",
            "song": "songofsolomon",
            "isaiah": "isaiah",
            "jeremiah": "jeremiah",
            "lamentations": "lamentations",
            "ezekiel": "ezekiel",
            "daniel": "daniel",
            "hosea": "hosea",
            "joel": "joel",
            "amos": "amos",
            "obadiah": "obadiah",
            "jonah": "jonah",
            "micah": "micah",
            "nahum": "nahum",
            "habakkuk": "habakkuk",
            "zephaniah": "zephaniah",
            "haggai": "haggai",
            "zechariah": "zechariah",
            "malachi": "malachi",
            "matthew": "matthew",
            "matt": "matthew",
            "mark": "mark",
            "luke": "luke",
            "john": "john",
            "acts": "acts",
            "romans": "romans",
            "1corinthians": "1corinthians",
            "icorinthians": "1corinthians",
            "i corinthians": "1corinthians",
            "1 corinthians": "1corinthians",
            "2corinthians": "2corinthians",
            "iicorinthians": "2corinthians",
            "ii corinthians": "2corinthians",
            "2 corinthians": "2corinthians",
            "galatians": "galatians",
            "ephesians": "ephesians",
            "philippians": "philippians",
            "colossians": "colossians",
            "1thessalonians": "1thessalonians",
            "ithessalonians": "1thessalonians",
            "i thessalonians": "1thessalonians",
            "1 thessalonians": "1thessalonians",
            "2thessalonians": "2thessalonians",
            "iithessalonians": "2thessalonians",
            "ii thessalonians": "2thessalonians",
            "2 thessalonians": "2thessalonians",
            "1timothy": "1timothy",
            "itimothy": "1timothy",
            "i timothy": "1timothy",
            "1 timothy": "1timothy",
            "2timothy": "2timothy",
            "iitimothy": "2timothy",
            "ii timothy": "2timothy",
            "2 timothy": "2timothy",
            "titus": "titus",
            "philemon": "philemon",
            "hebrews": "hebrews",
            "james": "james",
            "1peter": "1peter",
            "ipeter": "1peter",
            "i peter": "1peter",
            "1 peter": "1peter",
            "2peter": "2peter",
            "iipeter": "2peter",
            "ii peter": "2peter",
            "2 peter": "2peter",
            "1john": "1john",
            "ijohn": "1john",
            "i john": "1john",
            "1 john": "1john",
            "2john": "2john",
            "iijohn": "2john",
            "ii john": "2john",
            "2 john": "2john",
            "3john": "3john",
            "iiijohn": "3john",
            "iii john": "3john",
            "3 john": "3john",
            "jude": "jude",
            "revelation": "revelation",
            "rev": "revelation",
        }
        return mapping.get(compact, compact)

    def normalize_current_book(self) -> str:
        return self.normalize_book_name(self.book_var.get())


    def _candidate_book_names_for_lookup(self, book_name: str):
        canonical = self.normalize_book_name(book_name)
        candidates = [canonical]

        alias_groups = {
            "1samuel": ["1samuel", "isamuel"],
            "2samuel": ["2samuel", "iisamuel"],
            "1kings": ["1kings", "ikings"],
            "2kings": ["2kings", "iikings"],
            "1chronicles": ["1chronicles", "ichronicles"],
            "2chronicles": ["2chronicles", "iichronicles"],
            "1corinthians": ["1corinthians", "icorinthians"],
            "2corinthians": ["2corinthians", "iicorinthians"],
            "1thessalonians": ["1thessalonians", "ithessalonians"],
            "2thessalonians": ["2thessalonians", "iithessalonians"],
            "1timothy": ["1timothy", "itimothy"],
            "2timothy": ["2timothy", "iitimothy"],
            "1peter": ["1peter", "ipeter"],
            "2peter": ["2peter", "iipeter"],
            "1john": ["1john", "ijohn"],
            "2john": ["2john", "iijohn"],
            "3john": ["3john", "iiijohn"],
        }

        for alt in alias_groups.get(canonical, []):
            if alt not in candidates:
                candidates.append(alt)

        return candidates

    def current_verse(self):
        try:
            chapter = int(self.chapter_var.get() or 1)
            verse = int(self.verse_var.get() or 1)
        except Exception:
            chapter, verse = 1, 1

        translation = (self.translation_var.get() or "").strip().lower()
        row = None
        for candidate_book in self._candidate_book_names_for_lookup(self.normalize_current_book()):
            row = self.db.get_verse(
                translation,
                candidate_book,
                chapter,
                verse,
            )
            if row is not None:
                break
        return row

    def fetch_verse_text(self, book: str, chapter: int, verse: int, translation: str = "esv"):
        row = self.db.get_verse(translation, book, int(chapter), int(verse))
        return row.text if row else None

    def sanitize_display_text(self, value: str) -> str:
        return (value or "").replace("\r", " ").replace("\n", " ").strip()

    def parse_reference_label(self, ref: str):
        ref = (ref or "").strip()
        m = re.search(r"([1-3]?\s?[A-Za-z][A-Za-z\s]+?)\s+(\d+):(\d+)", ref)
        if not m:
            return None
        try:
            return (self.normalize_book_name(m.group(1).strip()), int(m.group(2)), int(m.group(3)))
        except Exception:
            return None

    def _render_clickable_strongs_summary(self, tags):
        if not tags:
            return

        clickable = []
        for t in tags:
            token = str(t.get("token") or "").strip()
            strongs = str(t.get("strongs") or "").strip().upper()
            if not strongs:
                continue
            if strongs.isdigit():
                strongs = f"G{strongs}"
            if token:
                clickable.append((token, strongs))

        if not clickable:
            return

        self.reader.insert("end", "Clickable Strong's Links:\n", ("section_header",))
        for i, (token, code) in enumerate(clickable):
            label = f"{token} ({code})"
            start_idx = self.reader.index("end")
            self.reader.insert("end", label)
            end_idx = self.reader.index(f"{start_idx}+{len(label)}c")
            tag = f"summary_strongs_{i}_{code}"
            self.reader.tag_add(tag, start_idx, end_idx)
            self._bind_reader_strongs_tag(tag, code)
            if i < len(clickable) - 1:
                self.reader.insert("end", "  •  ", ())
        self.reader.insert("end", "\n\n", ())


    def _insert_clickable_words(self, text: str, strongs_blob: str, verse=None):
        """
        Render verse text with inline clickable Strong's links.
        Formatting is locked so words are separated by spaces only.
        """
        safe_text = self.sanitize_display_text(text)
        if not verse:
            self.reader.insert("end", safe_text)
            return

        tags = self.get_token_tags_for_verse(verse.book, verse.chapter, verse.verse, verse.translation)
        if not tags:
            self.reader.insert("end", safe_text)
            return

        words = safe_text.split()
        tag_map = {t["position"]: t for t in tags if t["position"] is not None}

        for i, word in enumerate(words, start=1):
            start_idx = self.reader.index("end")
            self.reader.insert("end", word)
            end_idx = self.reader.index("end")

            if i in tag_map:
                strongs = str(tag_map[i]["strongs"]).strip().upper()
                if strongs and strongs[0] not in {"G", "H"} and strongs.isdigit():
                    strongs = f"G{strongs}"
                tag = f"inline_strongs_{i}_{strongs}"
                self.reader.tag_add(tag, start_idx, end_idx)
                self._bind_reader_strongs_tag(tag, strongs)

            if i < len(words):
                self.reader.insert("end", " ")

    def display_current_verse(self, startup: bool = False, skip_heavy_panels: bool = False) -> None:
        requested_book = self.normalize_current_book()
        try:
            requested_chapter = int(self.chapter_var.get() or 1)
            requested_verse = int(self.verse_var.get() or 1)
        except Exception:
            requested_chapter, requested_verse = 1, 1
            self.chapter_var.set(1)
            self.verse_var.set(1)

        translation = (self.translation_var.get() or "").strip().lower()
        verse = None
        for candidate_book in self._candidate_book_names_for_lookup(requested_book):
            verse = self.db.get_verse(
                translation,
                candidate_book,
                requested_chapter,
                requested_verse,
            )
            if verse is not None:
                break

        self.reader.delete("1.0", "end")
        if verse is None:
            self.reader.insert("end", "Verse not found in the database. Import Bible text or change the reference.")
            self.status_var.set("Verse not found")
            if not skip_heavy_panels:
                self.refresh_crossrefs_panel()
                self.refresh_compare_panel()
            return

        self.book_var.set(verse.book)
        self.chapter_var.set(verse.chapter)
        self.verse_var.set(verse.verse)

        context = self.db.get_context(verse.translation, verse.book, verse.chapter, verse.verse)
        self.reader.insert("end", f"{pretty_ref(verse.book, verse.chapter, verse.verse)} [{verse.translation.upper()}]\n\n")
        for row in context:
            self.reader.insert("end", f"{row.chapter}:{row.verse} ", ())
            if row.verse == verse.verse:
                self._insert_clickable_words(row.text, "", verse=row)
            else:
                self.reader.insert("end", self.sanitize_display_text(row.text), ())
            self.reader.insert("end", "\n\n", ())

        topics = self.topic_engine.detect(verse.text)
        if topics:
            self.reader.insert("end", "\nDetected Topics:\n")
            for idx, topic in enumerate(topics):
                start_idx = self.reader.index("end-1c")
                label = topic
                self.reader.insert("end", label)
                end_idx = self.reader.index(f"{start_idx} + {len(label)}c")
                tag = f"reader_topic_{idx}_{topic}"
                self.reader.tag_add(tag, start_idx, end_idx)
                self.reader.tag_config(tag, foreground="#1a73e8", underline=True)
                self.reader.tag_bind(tag, "<Button-1>", lambda e, q=topic: self.run_semantic_search_for_query(q))
                self.reader.tag_bind(tag, "<Enter>", lambda e: self.reader.config(cursor="hand2"))
                self.reader.tag_bind(tag, "<Leave>", lambda e: self.reader.config(cursor="xterm"))
                if idx < len(topics) - 1:
                    self.reader.insert("end", ", ")
                else:
                    self.reader.insert("end", "\n", ())
            try:
                self.search_entry.delete(0, "end")
                self.search_entry.insert(0, " ".join(topics[:5]))
            except Exception:
                pass

        clickable = self.build_top_clickable_strongs_list(
            verse.book, verse.chapter, verse.verse, verse.translation
        )
        if clickable:
            self.reader.tag_configure("section_header", font=("TkDefaultFont", 10, "bold"))
            self.reader.insert("end", "\nClickable Strong's Links:\n", ("section_header",))

            max_items = min(len(clickable), 20)
            for idx, (word, code) in enumerate(clickable[:max_items]):
                code = str(code).strip().upper()
                if code.isdigit():
                    code = f"G{code}"

                label = f"{word} ({code})"
                start_idx = self.reader.index("end-1c")
                self.reader.insert("end", label)
                end_idx = self.reader.index("end-1c")
                tag = f"top_strongs_{idx}_{code}"

                self.reader.tag_add(tag, start_idx, f"{end_idx}+1c")
                self._bind_reader_strongs_tag(tag, code)

                if idx < max_items - 1:
                    self.reader.insert("end", "  •  ", ())
                else:
                    self.reader.insert("end", " ")
        else:
            self.reader.insert("end", "\n(No Strong's data for this translation)\n")

        self.update_semantic_topics_panel(topics)
        self.status_var.set(f"Loaded {pretty_ref(verse.book, verse.chapter, verse.verse)}")
        if not skip_heavy_panels:
            self.refresh_crossrefs_panel()
            self.refresh_compare_panel()

        try:
            current = self.right_notebook.select()
            tab_text = self.right_notebook.tab(current, "text")
            if tab_text == "Commentary/Strong's":
                self._populate_commentary_tab_for_current_verse()
        except Exception:
            pass

    def update_semantic_topics_panel(self, topics):
        try:
            self.search_results.delete("1.0", "end")
            self.search_results.insert("end", "Detected Topics:\n\n")
            for topic in topics:
                start = self.search_results.index("end-1c")
                label = f"• {topic}\n"
                self.search_results.insert("end", label)
                end = self.search_results.index("end-1c")
                tag = f"topic_{topic}_{start.replace('.', '_')}"
                self.search_results.tag_add(tag, start, end)
                self.search_results.tag_config(tag, foreground="#1a73e8", underline=True)
                self.search_results.tag_bind(tag, "<Button-1>", lambda e, q=topic: self.run_semantic_search_for_query(q))
        except Exception:
            pass

    def refresh_compare_panel(self):
        self.compare_output.delete("1.0", "end")

        book = self.normalize_current_book()
        chapter = int(self.chapter_var.get())
        verse = int(self.verse_var.get())
        current = self.translation_var.get().strip().lower()

        seen = set()
        for tr in [current, "esv", "kjv", "web"]:
            if tr in seen:
                continue
            seen.add(tr)

            row = None
            for candidate_book in self._candidate_book_names_for_lookup(book):
                row = self.db.get_verse(
                    str(tr).strip().lower(),
                    candidate_book,
                    chapter,
                    verse,
                )
                if row:
                    break

            if row:
                self.compare_output.insert("end", f"[{tr.upper()}] {row.text}\n\n")
            else:
                self.compare_output.insert("end", f"[{tr.upper()}] Verse not available\n\n")

    def get_crossref_preview_rows_for_current(self):
        rows = []
        if not self.crossref_engine:
            return rows

        try:
            book = self.normalize_current_book()
            chapter = int(self.chapter_var.get() or 1)
            verse = int(self.verse_var.get() or 1)
        except Exception:
            return rows

        refs = []
        try:
            if hasattr(self.crossref_engine, "get_cross_references"):
                refs = self.crossref_engine.get_cross_references(book, chapter, verse, limit=50)
            elif hasattr(self.crossref_engine, "get_references"):
                refs = self.crossref_engine.get_references(book, chapter, verse, limit=50)
        except Exception:
            refs = []

        for r in refs:
            target_book = getattr(r, "target_book", None) or getattr(r, "target_book_start", "")
            target_chapter = getattr(r, "target_chapter", None) or getattr(r, "target_chapter_start", 0)
            target_verse = getattr(r, "target_verse", None) or getattr(r, "target_verse_start", 0)
            target_ref = getattr(r, "target_ref", "") or f"{str(target_book).title()} {target_chapter}:{target_verse}"
            if not target_book or not target_chapter or not target_verse:
                continue
            ref_label = target_ref
            preview_text = (
                self.fetch_verse_text(target_book, target_chapter, target_verse, translation=self.translation_var.get().strip().lower())
                or self.fetch_verse_text(target_book, target_chapter, target_verse, translation="esv")
                or "(verse text unavailable)"
            )
            rows.append({"ref": ref_label, "votes": getattr(r, "votes", 0), "text": preview_text})
        return rows

    def open_crossref_preview_window(self, ref_label: str, verse_text: str):
        top = tk.Toplevel(self.root)
        top.title(ref_label)
        top.geometry("760x300")
        frame = ttk.Frame(top, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=ref_label, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        text = tk.Text(frame, wrap="word", height=10)
        text.pack(fill="both", expand=True, pady=(8, 0))
        text.insert("1.0", self.sanitize_display_text(verse_text) or "(verse text unavailable)")
        text.configure(state="disabled")

    def refresh_crossrefs_panel(self):
        for child in self.crossrefs_container.winfo_children():
            child.destroy()
        rows = self.get_crossref_preview_rows_for_current()
        if not rows:
            ttk.Label(self.crossrefs_container, text="No cross references found.").pack(anchor="w", padx=6, pady=6)
            return
        for row in rows:
            outer = ttk.Frame(self.crossrefs_container, padding=(6, 6))
            outer.pack(fill="x", expand=True, anchor="n")
            header = ttk.Frame(outer)
            header.pack(fill="x", expand=True)
            ref_link = tk.Label(header, text=row["ref"], fg="#1a73e8", cursor="hand2", font=("TkDefaultFont", 10, "underline"))
            ref_link.pack(side="left", anchor="w")
            if row.get("votes"):
                ttk.Label(header, text=f"score {row['votes']}").pack(side="right", anchor="e")
            ref_link.bind("<Button-1>", lambda e, ref=row["ref"], text=row["text"]: self.open_crossref_preview_window(ref, text))
            preview = row.get("text", "") or "(verse text unavailable)"
            if len(preview) > 180:
                preview = preview[:177].rstrip() + "..."
            body = tk.Label(outer, text=preview, justify="left", anchor="w", wraplength=300, cursor="hand2")
            body.pack(fill="x", expand=True, anchor="w", pady=(4, 0))
            body.bind("<Button-1>", lambda e, ref=row["ref"], text=row["text"]: self.open_crossref_preview_window(ref, text))
            ttk.Separator(self.crossrefs_container).pack(fill="x", padx=6, pady=2)

    def open_text_popup(self, title: str, body: str):
        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("760x340")
        frame = ttk.Frame(top, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        text = tk.Text(frame, wrap="word")
        text.pack(fill="both", expand=True, pady=(8, 0))
        text.insert("1.0", body or "(no content)")
        text.configure(state="disabled")

    def render_study_guide(self, answer):
        self.assistant_output.delete("1.0", "end")
        self.assistant_output.insert("end", f"{answer.title}\n\n")
        self.assistant_output.insert("end", f"Summary\n{answer.summary}\n\n")

        self.assistant_output.insert("end", "Key Passages\n\n")
        for idx, item in enumerate(answer.key_passages):
            start = self.assistant_output.index("end-1c")
            self.assistant_output.insert("end", f"• {self.prettify_reference_label(item)}\n\n")
            end = self.assistant_output.index("end-1c")
            tag = f"study_passage_{idx}"
            self.assistant_output.tag_add(tag, start, end)
            self.assistant_output.tag_config(tag, foreground="#1a73e8", underline=True)
            self.assistant_output.tag_bind(tag, "<Button-1>", lambda e, ref=item: self.open_study_passage_popup(ref))

        self.assistant_output.insert("end", "Cross References\n\n")
        for idx, item in enumerate(answer.cross_references):
            start = self.assistant_output.index("end-1c")
            self.assistant_output.insert("end", f"• {self.prettify_reference_label(item)}\n\n")
            end = self.assistant_output.index("end-1c")
            tag = f"study_xref_{idx}"
            self.assistant_output.tag_add(tag, start, end)
            self.assistant_output.tag_config(tag, foreground="#1a73e8", underline=True)
            self.assistant_output.tag_bind(tag, "<Button-1>", lambda e, ref=item: self.open_study_passage_popup(ref))

        self.assistant_output.insert("end", "Reflection Questions\n\n")
        for item in answer.reflection_questions:
            self.assistant_output.insert("end", f"• {self.prettify_reference_label(item)}\n\n")

    def _clear_study_question_buttons(self):
        for child in self.study_questions_frame.winfo_children():
            child.destroy()

    def build_study_question_buttons(self, answer):
        self._clear_study_question_buttons()
        questions = [
            "What does this verse reveal about God?",
            "What command, promise, warning, or comfort is here?",
            "How could I apply this verse today?",
            "What other passage helps explain this verse?",
            "Which word in this verse deserves deeper study?",
        ]
        if answer:
            for q in getattr(answer, "reflection_questions", [])[:5]:
                if q not in questions:
                    questions.append(q)
        for q in questions[:8]:
            ttk.Button(self.study_questions_frame, text=q, command=lambda question=q: self.open_study_answer_popup(question)).pack(fill="x", pady=2)

    def navigate_to_reference(self, ref_text: str):
        parsed = self.parse_reference_label(ref_text)
        if not parsed:
            return False
        book, chapter, verse = parsed
        self.book_var.set(book)
        self.chapter_var.set(chapter)
        self.verse_var.set(verse)
        self.display_current_verse()
        try:
            self.right_notebook.select(self.compare_tab)
        except Exception:
            pass
        return True

    def open_study_passage_popup(self, ref_text: str):
        parsed = self.parse_reference_label(ref_text)
        if not parsed:
            self.open_text_popup(ref_text, "Passage preview unavailable.")
            return

        book, chapter, verse = parsed
        verse_text = self.fetch_verse_text(book, chapter, verse, translation=self.translation_var.get().strip().lower()) or self.fetch_verse_text(book, chapter, verse, translation="esv")
        commentary = ""
        try:
            row = self.db.get_verse(self.translation_var.get(), book, chapter, verse) or self.db.get_verse("esv", book, chapter, verse)
            if row:
                commentary = self.commentary_engine.explain(row)
        except Exception:
            commentary = ""

        top = tk.Toplevel(self.root)
        top.title(ref_text)
        top.geometry("780x420")

        frame = ttk.Frame(top, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=ref_text, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(6, 6))
        ttk.Button(btns, text="Open in Reader + Compare", command=lambda: (self.navigate_to_reference(ref_text), top.destroy())).pack(side="left")
        ttk.Button(btns, text="Semantic Search This Passage", command=lambda: (self.run_semantic_search_for_query(ref_text), top.destroy())).pack(side="left", padx=(6, 0))

        body = f"{ref_text}\n\n{self.sanitize_display_text(verse_text) or '(verse text unavailable)'}"
        if commentary:
            body += f"\n\nPossible Commentary\n{commentary}"

        text_widget = tk.Text(frame, wrap="word")
        text_widget.pack(fill="both", expand=True, pady=(4, 0))
        text_widget.insert("1.0", body)
        text_widget.configure(state="disabled")

    def open_study_answer_popup(self, question: str):
        verse = self.current_verse()
        if verse is None:
            return
        top = tk.Toplevel(self.root)
        top.title(question)
        top.geometry("760x340")
        frame = ttk.Frame(top, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=question, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        summary = [f"Reference: {pretty_ref(verse.book, verse.chapter, verse.verse)} [{verse.translation.upper()}]", "", "Verse", self.sanitize_display_text(verse.text), ""]
        commentary = ""
        try:
            commentary = self.commentary_engine.explain(verse)
        except Exception:
            pass
        if "God" in question or "reveal" in question.lower():
            summary += ["Possible Answer", "This verse should be read in light of God's character, purposes, and actions shown in the text."]
        elif "apply" in question.lower():
            summary += ["Possible Answer", "A practical application is to prayerfully consider what attitude, action, or trust this verse calls for today."]
        elif "other passage" in question.lower():
            refs = self.get_crossref_preview_rows_for_current()[:5]
            summary += ["Possible Answer"]
            if refs:
                summary.append("Helpful cross references:")
                summary += [f"- {r['ref']}" for r in refs]
            else:
                summary.append("Look for cross references and related themes to compare scripture with scripture.")
        elif "word" in question.lower() or "study" in question.lower():
            codes = self.build_top_clickable_strongs_list(verse.book, verse.chapter, verse.verse, verse.translation)
            summary += ["Possible Answer"]
            if codes:
                summary.append("Possible word-study candidates:")
                summary += [f"- {word} — {code}" for word, code in codes[:8]]
            else:
                summary.append("Choose a repeated, emphasized, or theologically important word for deeper study.")
        else:
            summary += ["Possible Answer", "Use the verse itself, its context, cross references, and word studies to build a careful answer."]
        if commentary:
            summary += ["", "Commentary", commentary]
        text = tk.Text(frame, wrap="word")
        text.pack(fill="both", expand=True, pady=(8, 0))
        text.insert("1.0", "\n".join(summary))
        text.configure(state="disabled")

    def refresh_timeline_panel(self):
        query_var = getattr(self, "timeline_filter_var", None)
        q = query_var.get().strip() if query_var else ""
        try:
            events = self.timeline_engine.search_events(q) if q else self.timeline_engine.get_all_events()
        except Exception as exc:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", f"Timeline engine error: {exc}")
            return

        selected_event_id = None
        if getattr(self, "_timeline_events_cache", None):
            sel = self.timeline_list.curselection()
            if sel:
                try:
                    selected_event_id = self._timeline_events_cache[sel[0]].id
                except Exception:
                    pass

        self._timeline_events_cache = events
        self.timeline_list.delete(0, "end")

        selected_index = None
        for i, event in enumerate(events):
            year = event.time_label or "Unknown time"
            label = f"{event.title} — {year}"
            try:
                label += f" [{self.timeline_engine.get_event_era(event)}]"
            except Exception:
                pass
            self.timeline_list.insert("end", label)
            if event.id == selected_event_id:
                selected_index = i

        if events:
            if selected_index is None:
                selected_index = 0
            self.timeline_list.selection_clear(0, "end")
            self.timeline_list.selection_set(selected_index)
            self.timeline_list.activate(selected_index)
            self.timeline_list.see(selected_index)
            self._debounced_timeline_select()
        else:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", "No timeline events found.")

    def filter_timeline_era(self, era: str):
        if not era:
            self.timeline_filter_var.set("")
            self._timeline_events_cache = self.timeline_engine.get_all_events()
        else:
            self.timeline_filter_var.set(era)
            self._timeline_events_cache = self.timeline_engine.get_events_for_era(era)

        self.timeline_list.delete(0, "end")
        for event in self._timeline_events_cache:
            year = event.time_label or "Unknown time"
            label = f"{event.title} — {year}"
            try:
                label += f" [{self.timeline_engine.get_event_era(event)}]"
            except Exception:
                pass
            self.timeline_list.insert("end", label)

        if self._timeline_events_cache:
            self.timeline_list.selection_clear(0, "end")
            self.timeline_list.selection_set(0)
            self.on_timeline_select()
        else:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", "No timeline events found for that era.")

    def filter_timeline_current_book(self):
        try:
            self.timeline_filter_var.set(self.normalize_current_book())
        except Exception:
            self.timeline_filter_var.set("")
        self.refresh_timeline_panel()

    def _debounced_timeline_select(self):
        if getattr(self, "_timeline_select_after_id", None):
            try:
                self.root.after_cancel(self._timeline_select_after_id)
            except Exception:
                pass

        self._timeline_select_after_id = self.root.after(120, self._perform_timeline_select)

    def _perform_timeline_select(self):
        self._timeline_select_after_id = None
        if not getattr(self, "_timeline_events_cache", None):
            return
        selection = self.timeline_list.curselection()
        if not selection:
            return
        event = self._timeline_events_cache[selection[0]]
        try:
            self.focus_on_event(event, open_compare_tab=False, update_map=False)
        except Exception:
            self.show_timeline_event_details(event)

    def on_timeline_select(self):
        if not getattr(self, "_timeline_events_cache", None):
            return
        if not self.timeline_list.curselection():
            return
        self._debounced_timeline_select()

    def open_selected_timeline_event_in_reader(self):
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return
        event = self._timeline_events_cache[selection[0]]
        self.focus_on_event(event, open_compare_tab=True, update_map=False)

    def open_selected_timeline_location_on_map(self):
        self._ensure_map_callback_server()
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return

        event = self._timeline_events_cache[selection[0]]
        if event.latitude is None or event.longitude is None:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", "This event does not have map coordinates.")
            return

        try:
            self.focus_on_event(event, open_compare_tab=False, update_map=True)
            output = getattr(self, "_last_highlighted_map", None) or self.map_engine.export_single_event_map(
                "exports/bible_timeline_selected_event.html",
                event=event,
                include_nearby=True,
            )
        except Exception as exc:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", f"Location map export failed: {exc}")
            return

        self.timeline_details.delete("1.0", "end")
        self.timeline_details.insert("end", f"Selected-event map exported to:\n{output}\n\n")
        self.timeline_details.insert("end", f"Centered on: {event.location_name} ({event.title})")
        try:
            import webbrowser
            webbrowser.open(f"file://{Path(output).resolve()}")
        except Exception:
            pass

    def show_selected_timeline_graph_links(self):
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return
        event = self._timeline_events_cache[selection[0]]
        self.focus_on_event(event, open_compare_tab=False, update_map=False)
        try:
            self.right_notebook.select(self.graph_tab)
        except Exception:
            pass

    def open_timeline_map(self):
        self._ensure_map_callback_server()
        try:
            output = self.map_engine.export_map("exports/bible_timeline_map.html")
        except Exception as exc:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", f"Map export failed: {exc}")
            if hasattr(self, "map_preview_status_var"):
                self.map_preview_status_var.set(f"Full map export failed: {exc}")
            return
        self.timeline_details.delete("1.0", "end")
        self.timeline_details.insert("end", f"Map exported to:\n{output}")
        if hasattr(self, "map_preview_status_var"):
            self.map_preview_status_var.set(f"Full timeline map ready: {output}")
        try:
            webbrowser.open(f"file://{Path(output).resolve()}")
        except Exception:
            pass

    def open_timeline_event_reference(self, ref_text: str):
        parsed = self.parse_reference_label(ref_text)
        if not parsed:
            return False

        book, chapter, verse = parsed
        self.book_var.set(book)
        self.chapter_var.set(chapter)
        self.verse_var.set(verse)

        self.display_current_verse()

        try:
            self.refresh_crossrefs_panel()
            self.refresh_compare_panel()
            self.run_semantic_search_for_query(ref_text)
        except Exception:
            pass

        return True

    def search_selected_timeline_event(self):
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return
        event = self._timeline_events_cache[selection[0]]
        self.focus_on_event(event, open_compare_tab=False, update_map=False)

    def start_map_callback_server(self):
        app = self

        class MapCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)

                if parsed.path != "/open":
                    self.send_response(404)
                    self.end_headers()
                    return

                params = urllib.parse.parse_qs(parsed.query)

                try:
                    book = params.get("book", [""])[0]
                    chapter = int(params.get("chapter", ["0"])[0])
                    verse = int(params.get("verse", ["0"])[0])
                except Exception:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Bad request")
                    return

                def update_app():
                    try:
                        app.book_var.set(book)
                        app.chapter_var.set(chapter)
                        app.verse_var.set(verse)
                        app.display_current_verse()
                        app.refresh_crossrefs_panel()
                        app.refresh_compare_panel()
                        app.run_semantic_search_for_query(f"{book} {chapter}:{verse}")
                        try:
                            app.right_notebook.select(app.compare_tab)
                        except Exception:
                            pass
                    except Exception as exc:
                        print("Map callback error:", exc)

                app.root.after(0, update_app)

                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body><h3>Opened in Bible Reader.</h3><p>You can return to the app.</p></body></html>")

            def log_message(self, format, *args):
                return

        try:
            self._map_callback_server = HTTPServer(("127.0.0.1", 8765), MapCallbackHandler)
            thread = threading.Thread(target=self._map_callback_server.serve_forever, daemon=True)
            thread.start()
        except Exception as exc:
            print("Could not start map callback server:", exc)

    def handle_graph_navigation(self, node_type: str, label: str):
        value = (label or "").strip()
        if not value:
            return

        if node_type == "reference":
            self.open_timeline_event_reference(value)
            try:
                self.right_notebook.select(self.compare_tab)
            except Exception:
                pass
            return

        if node_type == "person":
            self.timeline_filter_var.set(value)
            try:
                events = self.timeline_engine.get_events_for_person(value)
            except Exception:
                events = self.timeline_engine.search_events(value)

            self._timeline_events_cache = events
            self.timeline_list.delete(0, "end")
            for event in events:
                year = event.time_label or "Unknown time"
                label_text = f"{event.title} — {year}"
                try:
                    label_text += f" [{self.timeline_engine.get_event_era(event)}]"
                except Exception:
                    pass
                self.timeline_list.insert("end", label_text)

            if events:
                self.timeline_list.selection_clear(0, "end")
                self.timeline_list.selection_set(0)
                self.timeline_list.activate(0)
                self.timeline_list.see(0)
                self._debounced_timeline_select()

            try:
                self.right_notebook.select(self.timeline_tab)
            except Exception:
                pass
            return

        if node_type == "place":
            self.timeline_filter_var.set(value)
            try:
                events = self.timeline_engine.get_events_for_location(value)
            except Exception:
                events = self.timeline_engine.search_events(value)

            self._timeline_events_cache = events
            self.timeline_list.delete(0, "end")
            for event in events:
                year = event.time_label or "Unknown time"
                label_text = f"{event.title} — {year}"
                try:
                    label_text += f" [{self.timeline_engine.get_event_era(event)}]"
                except Exception:
                    pass
                self.timeline_list.insert("end", label_text)

            if events:
                self.timeline_list.selection_clear(0, "end")
                self.timeline_list.selection_set(0)
                self.timeline_list.activate(0)
                self.timeline_list.see(0)
                self._debounced_timeline_select()
                try:
                    self.update_map_explorer_for_event(events[0], auto_generate=True)
                except Exception:
                    pass

            try:
                self.right_notebook.select(self.timeline_tab)
            except Exception:
                pass
            return

        if node_type == "theme":
            try:
                self.search_entry.delete(0, "end")
                self.search_entry.insert(0, value)
            except Exception:
                pass
            self._run_semantic_search_threaded(value)
            try:
                self.right_notebook.select(self.study_tab)
            except Exception:
                pass
            return

    def navigate_graph_node(self, node_type: str, label: str):
        self.handle_graph_navigation(node_type, label)

    def _open_graph_node_menu(self, event, node_type: str, label: str):
        try:
            if self._graph_nav_menu is None:
                self._graph_nav_menu = tk.Menu(self.root, tearoff=0)
            else:
                self._graph_nav_menu.delete(0, "end")
            self._graph_nav_menu.add_command(
                label=f"Navigate: {label}",
                command=lambda nt=node_type, lb=label: self.handle_graph_navigation(nt, lb),
            )
            self._graph_nav_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._graph_nav_menu.grab_release()
            except Exception:
                pass

    def update_graph_view_for_event(self, event):
        if not hasattr(self, "graph_output"):
            return
        nodes, edges = self.event_graph_bridge.event_to_graph_bundle(event.id)
        self.graph_event_label_var.set(f"Knowledge Graph Focus: {event.title}")

        self.graph_output.delete("1.0", "end")
        self.graph_output.insert("end", f"{event.title}\n\n")
        self.graph_output.insert("end", f"Reference: {event.reference}\n")
        self.graph_output.insert("end", f"Time: {event.time_label or 'Unknown'}\n")
        self.graph_output.insert("end", f"Location: {event.location_name or 'Unknown'}\n\n")
        self.graph_output.insert("end", "Nodes\n")

        for idx, node in enumerate(nodes):
            line = f"• {node.node_type}: {node.label}\n"
            start_idx = self.graph_output.index("end-1c")
            self.graph_output.insert("end", line)
            end_idx = self.graph_output.index("end-1c")
            tag = f"graph_node_{idx}"
            self.graph_output.tag_add(tag, start_idx, end_idx)
            self.graph_output.tag_config(tag, foreground="#1a73e8", underline=True)
            self.graph_output.tag_bind(tag, "<Button-1>", lambda e, nt=node.node_type, lb=node.label: self.root.after(10, lambda: self.handle_graph_navigation(nt, lb)))
            self.graph_output.tag_bind(tag, "<Button-3>", lambda e, nt=node.node_type, lb=node.label: self._open_graph_node_menu(e, nt, lb))
            self.graph_output.tag_bind(tag, "<Enter>", lambda e: self.graph_output.config(cursor="hand2"))
            self.graph_output.tag_bind(tag, "<Leave>", lambda e: self.graph_output.config(cursor="xterm"))

        self.graph_output.insert("end", "\nEdges\n")
        for edge in edges:
            self.graph_output.insert("end", f"• {edge.source} -> {edge.target} ({edge.relation})\n")

    def show_selected_timeline_in_graph_view(self):
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return
        event = self._timeline_events_cache[selection[0]]
        self.update_graph_view_for_event(event)
        try:
            self.right_notebook.select(self.graph_tab)
        except Exception:
            pass

    def _active_tab_name(self):
        try:
            return self.right_notebook.tab(self.right_notebook.select(), "text")
        except Exception:
            return ""

    def _update_reader_fast(self, event):
        self.book_var.set(event.book)
        self.chapter_var.set(event.chapter_start)
        self.verse_var.set(event.verse_start)
        self.display_current_verse()

    def show_timeline_event_details(self, event):
        self.timeline_details.delete("1.0", "end")
        self.timeline_details.insert("end", f"{event.title}\n\n")
        self.timeline_details.insert("end", f"Reference: {event.reference}\n")
        self.timeline_details.insert("end", "Unified Study Mode active: Reader, Compare, Cross Refs, Semantic Search, and Graph are synced.\n")
        self.timeline_details.insert("end", f"Time: {event.time_label or 'Unknown'}\n")

        self.timeline_details.insert("end", "Location: ")
        loc_start = self.timeline_details.index("end")
        self.timeline_details.insert("end", f"{event.location_name or 'Unknown'}")
        loc_end = self.timeline_details.index("end")
        self.timeline_details.insert("end", "\n")

        if event.location_name and event.latitude is not None and event.longitude is not None:
            tag = f"timeline_location_{event.id}"
            self.timeline_details.tag_add(tag, loc_start, loc_end)
            self.timeline_details.tag_config(tag, foreground="#1a73e8", underline=True)
            self.timeline_details.tag_bind(tag, "<Button-1>", lambda e: self.open_selected_timeline_location_on_map())
            self.timeline_details.tag_bind(tag, "<Enter>", lambda e: self.timeline_details.config(cursor="hand2"))
            self.timeline_details.tag_bind(tag, "<Leave>", lambda e: self.timeline_details.config(cursor="xterm"))

        self.timeline_details.insert("end", f"Type: {event.event_type or 'Unknown'}\n")
        if event.people:
            self.timeline_details.insert("end", f"People: {', '.join(event.people)}\n")
        if event.tags:
            self.timeline_details.insert("end", f"Tags: {', '.join(event.tags)}\n")
        self.timeline_details.insert("end", "\n")
        self.timeline_details.insert("end", event.summary or "(no summary)")

    def highlight_map_event(self, event):
        try:
            cache_key = f"{event.id}:selected"
            if cache_key in self._map_cache:
                output = self._map_cache[cache_key]
            else:
                output = self.map_engine.export_single_event_map(
                    "exports/bible_timeline_selected_event.html",
                    event=event,
                    include_nearby=True,
                )
                self._map_cache[cache_key] = output
            self._last_highlighted_map = output
            return output
        except Exception:
            return None

    def focus_on_event(self, event, *, open_compare_tab: bool = False, update_map: bool = False):
        if getattr(self, "_last_focused_event_id", None) == event.id and not update_map:
            try:
                self.show_timeline_event_details(event)
                self.update_map_explorer_for_event(event, auto_generate=False)
            except Exception:
                pass
            if open_compare_tab:
                try:
                    self.right_notebook.select(self.compare_tab)
                except Exception:
                    pass
            return

        self._last_focused_event_id = event.id

        self._update_reader_fast(event)

        try:
            self.show_timeline_event_details(event)
        except Exception:
            pass

        try:
            self.update_map_explorer_for_event(event, auto_generate=update_map)
        except Exception:
            pass

        semantic_query = event.title
        if getattr(event, "tags", None):
            semantic_query += " " + " ".join(event.tags[:3])
        try:
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, semantic_query)
        except Exception:
            pass

        self.root.after(50, lambda: self.refresh_crossrefs_panel())
        self.root.after(100, lambda: self.refresh_compare_panel())
        self.root.after(150, lambda q=semantic_query: self._run_semantic_search_threaded(q))

        try:
            self.update_graph_view_for_event(event)
        except Exception:
            pass

        if update_map:
            self.root.after(200, lambda: self.highlight_map_event(event))

        if open_compare_tab:
            try:
                self.right_notebook.select(self.compare_tab)
            except Exception:
                pass

    def _deliver_semantic_search_results(self, token, query, hits, error=None):
        if token != getattr(self, "_active_semantic_search_token", 0):
            return

        self.search_results.delete("1.0", "end")

        if error:
            self.search_results.insert("end", f"Semantic search failed: {error}")
            self.status_var.set("Semantic search failed")
            return

        if not hits:
            self.search_results.insert("end", "No results. Import more Bible text or broaden the query.")
            self.status_var.set("Semantic search complete: 0 results")
            return

        engine_mode = getattr(self.semantic_engine, "mode", "semantic")
        self.search_results.insert("end", f"Semantic engine mode: {engine_mode}\n\n")

        for idx, hit in enumerate(hits):
            verse_obj = getattr(hit, "verse", None)
            if verse_obj is not None:
                ref = pretty_ref(verse_obj.book, verse_obj.chapter, verse_obj.verse)
                body = self.sanitize_display_text(verse_obj.text)
                translation = verse_obj.translation.upper()
            else:
                ref = "Unknown reference"
                body = ""
                translation = "N/A"

            score = getattr(hit, "score", None)

            clickable_label = f"{ref} [{translation}]"
            start = self.search_results.index("end-1c")
            self.search_results.insert("end", clickable_label)
            end = self.search_results.index("end-1c")

            if verse_obj is not None:
                tag = f"search_ref_{idx}"
                self.search_results.tag_add(tag, start, end)
                self.search_results.tag_configure(tag, foreground="#1a73e8", underline=1)
                self.search_results.tag_bind(
                    tag,
                    "<Button-1>",
                    lambda e, h=hit: self._handle_semantic_click(e, h)
                )
                self.search_results.tag_bind(
                    tag,
                    "<Enter>",
                    lambda e, h=hit: (
                        self.search_results.config(cursor="hand2"),
                        self._show_semantic_result_tooltip(e, h)
                    )
                )
                self.search_results.tag_bind(
                    tag,
                    "<Leave>",
                    lambda e: (
                        self.search_results.config(cursor="xterm"),
                        self._hide_semantic_result_tooltip()
                    )
                )

            if score is not None:
                header = f"{ref} [{translation}]  score={score:.3f}"
            else:
                header = f"{ref} [{translation}]"

            start = self.search_results.index("end")
            self.search_results.insert("end", header + "\n")
            end = self.search_results.index("end")
            tag = f"search_ref_{idx}"
            self.search_results.tag_add(tag, start, end)
            self.search_results.tag_config(tag, foreground="#1a73e8", underline=True)
            self.search_results.tag_bind(tag, "<Enter>", lambda e: self.search_results.config(cursor="hand2"))
            self.search_results.tag_bind(tag, "<Leave>", lambda e: self.search_results.config(cursor="xterm"))

            if body:
                self.search_results.insert("end", body + "\n\n")
            else:
                self.search_results.insert("end", "\n")

        self.status_var.set(f"Semantic search complete: {len(hits)} results ({engine_mode})")


    def _toggle_semantic_preview(self, verse_obj):
        key = (
            verse_obj.translation.lower(),
            verse_obj.book.lower(),
            int(verse_obj.chapter),
            int(verse_obj.verse),
        )

        if key in self._semantic_preview_collapsed:
            self._semantic_preview_collapsed.remove(key)
        else:
            self._semantic_preview_collapsed.add(key)

        self._render_semantic_preview_stack()


    def _render_semantic_preview_stack(self):
        if not hasattr(self, "commentary_output"):
            return

        w = self.commentary_output
        w.delete("1.0", "end")

        if not self._semantic_preview_stack:
            w.insert("end", "No semantic previews yet.\n")
            return

        w.insert("end", "Semantic Preview Stack\n\n")
        w.tag_configure("semantic_stack_title", font=("TkDefaultFont", 10, "bold"))
        w.tag_add("semantic_stack_title", "1.0", "1.end")

        for idx, verse_obj in enumerate(self._semantic_preview_stack, start=1):
            key = (
                verse_obj.translation.lower(),
                verse_obj.book.lower(),
                int(verse_obj.chapter),
                int(verse_obj.verse),
            )
            collapsed = key in self._semantic_preview_collapsed
            marker = "▶" if collapsed else "▼"

            ref = pretty_ref(verse_obj.book, verse_obj.chapter, verse_obj.verse)
            clickable_label = f"{idx}. {marker} {ref} [{verse_obj.translation.upper()}]"
            remove_label = "   [remove]"

            # clickable verse ref
            ref_tag = f"semantic_preview_ref_{idx}_{verse_obj.book}_{verse_obj.chapter}_{verse_obj.verse}"
            ref_start = w.index("end-1c")
            w.insert("end", clickable_label)
            ref_end = f"{ref_start}+{len(clickable_label)}c"

            w.tag_add(ref_tag, ref_start, ref_end)
            w.tag_configure(
                ref_tag,
                foreground="#1a73e8",
                underline=1,
                font=("TkDefaultFont", 10, "bold"),
            )
            w.tag_bind(ref_tag, "<Button-1>", lambda e, v=verse_obj: self._toggle_semantic_preview(v))
            w.tag_bind(ref_tag, "<Enter>", lambda e: w.config(cursor="hand2"))
            w.tag_bind(ref_tag, "<Leave>", lambda e: w.config(cursor="xterm"))
            w.tag_raise(ref_tag)

            # clickable remove
            remove_tag = f"semantic_preview_remove_{idx}"
            remove_start = w.index("end-1c")
            w.insert("end", remove_label)
            remove_end = f"{remove_start}+{len(remove_label)}c"

            w.tag_add(remove_tag, remove_start, remove_end)
            w.tag_configure(remove_tag, foreground="#b00020", underline=1)
            w.tag_bind(remove_tag, "<Button-1>", lambda e, i=idx - 1: self._remove_semantic_preview_at(i))
            w.tag_bind(remove_tag, "<Enter>", lambda e: w.config(cursor="hand2"))
            w.tag_bind(remove_tag, "<Leave>", lambda e: w.config(cursor="xterm"))
            w.tag_raise(remove_tag)

            # end header line
            w.insert("end", "\n")

            # body
            if not collapsed:
                w.insert("end", self.sanitize_display_text(verse_obj.text or ""))
                w.insert("end", "\n\n")

                crossrefs = self._semantic_preview_crossrefs_text(verse_obj)
                if crossrefs:
                    w.insert("end", crossrefs + "\n\n")
            else:
                w.insert("end", "\n")
            # divider between items
            if idx < len(self._semantic_preview_stack):
                w.insert("end", self._semantic_preview_divider())
                w.insert("end", "\n\n")

        # clear all
        clear_tag = "semantic_preview_clear_all"
        clear_label = "[Clear all semantic previews]"
        clear_start = w.index("end-1c")
        w.insert("end", clear_label)
        clear_end = f"{clear_start}+{len(clear_label)}c"

        w.tag_add(clear_tag, clear_start, clear_end)
        w.tag_configure(
            clear_tag,
            foreground="#b00020",
            underline=1,
            font=("TkDefaultFont", 10, "bold"),
        )
        w.tag_bind(clear_tag, "<Button-1>", lambda e: self._clear_semantic_preview_stack())
        w.tag_bind(clear_tag, "<Enter>", lambda e: w.config(cursor="hand2"))
        w.tag_bind(clear_tag, "<Leave>", lambda e: w.config(cursor="xterm"))
        w.tag_raise(clear_tag)

        w.insert("end", "\n\nTip: Click a blue reference above to expand/collapse it.\n")

    def _semantic_preview_crossrefs_text(self, verse_obj, limit: int = 8) -> str:
        try:
            if not self.crossref_engine:
                return ""

            refs = []

            if hasattr(self.crossref_engine, "get_reference_labels"):
                refs = self.crossref_engine.get_reference_labels(
                    verse_obj.book,
                    int(verse_obj.chapter),
                    int(verse_obj.verse),
                    limit=limit,
                )
            elif hasattr(self.crossref_engine, "get_references"):
                hits = self.crossref_engine.get_references(
                    verse_obj.book,
                    int(verse_obj.chapter),
                    int(verse_obj.verse),
                    limit=limit,
                )
                refs = [
                    getattr(hit, "target_ref", None)
                    or getattr(hit, "ref", None)
                    or str(hit)
                    for hit in hits
                ]

            if not refs:
                return ""

            lines = ["Cross references:"]
            for ref in refs[:limit]:
                lines.append(f"  • {ref}")
            return "\n".join(lines)

        except Exception:
            return ""

    def _semantic_preview_divider(self) -> str:
        try:
            widget = self.commentary_output
            pixel_width = max(widget.winfo_width(), 200)
            avg_char_px = 8
            chars = max(20, min(120, (pixel_width // avg_char_px) - 4))
            return "  " + ("─" * max(16, chars - 4)) + "  "
        except Exception:
            return "─" * 56

    def _open_semantic_preview_verse(self, verse_obj):
        try:
            self.book_var.set(verse_obj.book)
            self.chapter_var.set(verse_obj.chapter)
            self.verse_var.set(verse_obj.verse)
            self.translation_var.set(verse_obj.translation)
            self.display_current_verse()
        except Exception as exc:
            try:
                messagebox.showerror("Semantic Preview", f"Could not open verse:\n\n{exc}")
            except Exception:
                pass

    def _preview_semantic_hit(self, hit):
        verse_obj = getattr(hit, "verse", None)
        if verse_obj is None:
            return

        key = (
            verse_obj.translation.lower(),
            verse_obj.book.lower(),
            int(verse_obj.chapter),
            int(verse_obj.verse),
        )

        existing_keys = {
            (
                v.translation.lower(),
                v.book.lower(),
                int(v.chapter),
                int(v.verse),
            )
            for v in self._semantic_preview_stack
        }

        if key not in existing_keys:
            self._semantic_preview_stack.append(verse_obj)

        try:
            self.right_notebook.select(self.commentary_tab)
        except Exception:
            pass

        self._render_semantic_preview_stack()
        self.status_var.set(
            f"Previewed {pretty_ref(verse_obj.book, verse_obj.chapter, verse_obj.verse)}"
        )


    def _handle_semantic_click(self, event, hit):
        try:
            self._hide_semantic_result_tooltip()
        except Exception:
            pass

        verse_obj = getattr(hit, "verse", None)
        if verse_obj is None:
            return

        # Shift+click only -> open in reader
        if (event.state & 0x0001) != 0:
            self._open_semantic_hit_in_reader(hit)
            return

        # Normal click -> preview stack only
        self._preview_semantic_hit(hit)

    def _run_semantic_search_threaded(self, query: str):
        token = next(self._semantic_search_counter)
        self._active_semantic_search_token = token
        self.search_results.delete("1.0", "end")
        self.search_results.insert("end", f"Searching for: {query}\n\nWorking...")
        self.status_var.set("Semantic search running")

        def worker():
            try:
                engine = self._ensure_semantic_engine()
                hits = engine.search(query, limit=20)
                self.root.after(0, lambda: self._deliver_semantic_search_results(token, query, hits, None))
            except Exception as exc:
                self.root.after(0, lambda exc=exc: self._deliver_semantic_search_results(token, query, [], str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def run_semantic_search_for_query(self, query: str):
        try:
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, query)
        except Exception:
            pass

        try:
            self.right_notebook.select(self.study_tab)
        except Exception:
            pass

        try:
            self._ensure_semantic_engine()
        except Exception as exc:
            self.search_results.delete("1.0", "end")
            self.search_results.insert("end", f"Could not load semantic engine:\n{exc}")
            self.status_var.set("Semantic engine load failed")
            return

        self._run_semantic_search_threaded(query)

    def run_semantic_search(self) -> None:
        query = self.search_entry.get().strip()
        try:
            self.right_notebook.select(self.study_tab)
        except Exception:
            pass
        try:
            self._ensure_semantic_engine()
        except Exception as exc:
            self.search_results.delete("1.0", "end")
            self.search_results.insert("end", f"Could not load semantic engine:\n{exc}")
            self.status_var.set("Semantic engine load failed")
            return
        if not query:
            self.search_results.delete("1.0", "end")
            return
        self._run_semantic_search_threaded(query)

    def _open_semantic_hit_in_reader(self, hit):
        self._hide_semantic_result_tooltip()
        try:
            verse_obj = getattr(hit, "verse", None)
            if verse_obj is None:
                return
            self.book_var.set(verse_obj.book)
            self.chapter_var.set(verse_obj.chapter)
            self.verse_var.set(verse_obj.verse)
            self.translation_var.set(verse_obj.translation)
            self.display_current_verse()
        except Exception as exc:
            try:
                messagebox.showerror("Semantic Result", f"Could not open verse:\n\n{exc}")
            except Exception:
                pass

    def open_semantic_result_popup(self, hit):
        top = tk.Toplevel(self.root)
        ref = pretty_ref(hit.verse.book, hit.verse.chapter, hit.verse.verse)
        top.title(ref)
        top.geometry("820x380")
        frame = ttk.Frame(top, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"{ref} [{hit.verse.translation.upper()}]", font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        body = [hit.verse.text, ""]
        try:
            body += ["Possible Commentary", self.commentary_engine.explain(hit.verse)]
        except Exception:
            pass
        text = tk.Text(frame, wrap="word")
        text.pack(fill="both", expand=True, pady=(8, 0))
        text.insert("1.0", "\n".join(body))
        text.configure(state="disabled")

    def run_ai_assistant(self) -> None:
        question = self.question_entry.get().strip() if hasattr(self, "question_entry") else ""
        if not question:
            question = "What does this verse teach?"
        try:
            study_assistant = self._ensure_study_assistant()
        except Exception as exc:
            try:
                messagebox.showerror("Study Guide", f"Could not load study assistant:\n\n{exc}")
            except Exception:
                pass
            self.status_var.set("Study assistant load failed")
            return
        answer = study_assistant.answer(question)
        self.render_study_guide(answer)
        self.build_study_question_buttons(answer)
        self.status_var.set("Study guide generated")

    def _bind_commentary_strongs_tag(self, tag: str, code: str):
        code = str(code or "").strip().upper()
        if code.isdigit():
            code = f"G{code}"

        self.commentary_output.tag_configure(
            tag,
            foreground="blue",
            underline=1
        )

        self.commentary_output.tag_bind(
            tag,
            "<Button-1>",
            lambda e, c=code: self._safe_open_strongs_code(str(c), event=e)
        )

        self.commentary_output.tag_bind(
            tag,
            "<Button-3>",
            lambda e, c=code: self._show_strongs_context_menu(e, str(c))
        )

        self.commentary_output.tag_bind(
            tag,
            "<Enter>",
            lambda e, t=tag, c=code: (
                self.commentary_output.config(cursor="hand2"),
                self.commentary_output.tag_configure(
                    t,
                    foreground="blue",
                    underline=1,
                    background="#eef6ff"
                ),
                self._show_strongs_tooltip(e, str(c))
            )
        )

        self.commentary_output.tag_bind(
            tag,
            "<Leave>",
            lambda e, t=tag: (
                self.commentary_output.config(cursor="xterm"),
                self.commentary_output.tag_configure(
                    t,
                    foreground="blue",
                    underline=1,
                    background=""
                ),
                self._hide_strongs_tooltip()
            )
        )

    def generate_commentary(self) -> None:
        try:
            self.right_notebook.select(self.commentary_tab)
        except Exception:
            pass
        verse = self.current_verse()
        self.commentary_output.delete("1.0", "end")
        if verse is None:
            self.commentary_output.insert("end", "Verse not found.")
            return

        self.commentary_output.insert("end", self.commentary_engine.explain(verse), ())
        links = self.build_top_clickable_strongs_list(
            verse.book, verse.chapter, verse.verse, verse.translation
        )

        if links:
            self.commentary_output.tag_configure(
                "section_header",
                font=("TkDefaultFont", 10, "bold")
            )
            self.commentary_output.insert(
                "end",
                "\n\nWord / Strong's Links\n",
                ("section_header",)
            )

            for idx, (word, code) in enumerate(links[:15]):
                code = str(code).strip().upper()
                if code.isdigit():
                    code = f"G{code}"

                lemma = ""
                try:
                    result = self.strongs_engine.study_code(code)
                    entry = getattr(result, "entry", None)
                    lemma = str(getattr(entry, "lemma", "") or "").strip()
                except Exception:
                    lemma = ""

                self.commentary_output.insert("end", f"- {word} — ", ())

                tag = f"commentary_strongs_{idx}_{code}"
                self.commentary_output.insert("end", code, (tag,))
                self._bind_commentary_strongs_tag(tag, code)

                if lemma:
                    self.commentary_output.insert("end", f" ({lemma})", ())

                self.commentary_output.insert("end", "\n", ())

        self.status_var.set("Commentary generated")


    def open_strongs_code(self, code: str) -> None:
        self.strongs_query_var.set(str(code))
        try:
            self.right_notebook.select(self.commentary_tab)
        except Exception:
            pass
        self.run_strongs_lookup()

    def run_strongs_lookup(self) -> None:
        try:
            self.right_notebook.select(self.commentary_tab)
        except Exception:
            pass
        query = self.strongs_query_var.get().strip()
        self.commentary_output.delete("1.0", "end")
        if not query:
            return

        verse = self.current_verse()
        word_map = self.build_top_clickable_strongs_list(
            verse.book, verse.chapter, verse.verse, verse.translation
        ) if verse else []

        try:
            strongs_engine = self._ensure_strongs_engine()
        except Exception as exc:
            self.commentary_output.insert("end", f"Could not load Strong's engine:\n{exc}")
            self.status_var.set("Strong's engine load failed")
            return

        normalized = query.upper()
        if normalized[:1] in {"G", "H"} and normalized[1:].isdigit():
            try:
                result = strongs_engine.study_code(normalized)
                self._strongs_result_cache[normalized] = result
            except Exception as exc:
                self.commentary_output.insert("end", f"Could not open Strong's code {normalized}:\n{exc}")
                self.status_var.set("Strong's lookup failed")
                return

            if result.entry is None:
                self.commentary_output.insert("end", f"No Strong's entry found for {normalized}.\n")
            else:
                entry = result.entry
                matching_words = [w for w, c in word_map if c.upper() == normalized]
                if matching_words:
                    self.commentary_output.insert("end", f"Word(s): {', '.join(sorted(set(matching_words)))}\n")
                self.commentary_output.insert("end", f"{entry.strongs_id} — {entry.lemma}\n")
                self.commentary_output.insert("end", f"Transliteration: {entry.transliteration or 'N/A'}\n")
                self.commentary_output.insert("end", f"Language: {entry.language}\n")
                self.commentary_output.insert("end", f"Gloss: {entry.gloss or 'N/A'}\n\n")
                self.commentary_output.insert("end", f"Definition\n{entry.definition}\n\n")
                self.commentary_output.insert("end", "Occurrences\n")
                for occ in getattr(result, "occurrences", []) or []:
                    self.commentary_output.insert("end", f"- {occ}\n")
            self.status_var.set(f"Strong's lookup complete: {normalized}")
            return

        try:
            hits = strongs_engine.search(query)
        except Exception as exc:
            self.commentary_output.insert("end", f"Strong's search failed:\n{exc}")
            self.status_var.set("Strong's search failed")
            return

        if not hits:
            self.commentary_output.insert("end", f"No Strong's entries found for '{query}'.")
            self.status_var.set("No Strong's matches found")
            return

        self.commentary_output.insert("end", f"Strong's search results for '{query}'\n\n")
        for idx, hit in enumerate(hits[:25], start=1):
            strongs_id = getattr(hit, "strongs_id", "") or getattr(hit, "code", "")
            lemma = getattr(hit, "lemma", "") or ""
            transliteration = getattr(hit, "transliteration", "") or "N/A"
            gloss = getattr(hit, "gloss", "") or "N/A"

            label = f"{idx}. {strongs_id} — {lemma}\n"
            start = self.commentary_output.index("end")
            self.commentary_output.insert("end", label)
            end = self.commentary_output.index("end")

            tag = f"strongs_search_hit_{idx}_{strongs_id}"
            self.commentary_output.tag_add(tag, start, end)
            self._bind_commentary_strongs_tag(tag, strongs_id)

            self.commentary_output.insert("end", f"   Transliteration: {transliteration}\n")
            self.commentary_output.insert("end", f"   Gloss: {gloss}\n\n")

        self.status_var.set(f"Strong's search complete: {query}")

    def export_graph(self) -> None:
        try:
            html_path = self.graph_engine.export_html()
        except Exception as exc:
            messagebox.showerror("Knowledge Graph", f"Could not export graph: {exc}")
            self.status_var.set("Knowledge graph export failed")
            return
        self.status_var.set(f"Knowledge graph exported to {html_path}")
        if Path(html_path).exists():
            webbrowser.open(f"file://{html_path}")

    def import_bible(self) -> None:
        path = filedialog.askopenfilename(title="Select Bible file", filetypes=[("Bible Files", "*.txt *.pipe *.csv *.jsonl"), ("All Files", "*.*")])
        if not path:
            return
        translation = self.import_translation_var.get().strip().lower() or None
        fmt = self.import_format_var.get().strip().lower()
        fmt = None if fmt == "auto" else fmt
        try:
            records = list(parse_bible_file(path, translation=translation, fmt=fmt))
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        imported = self.db.bulk_import(records)
        self.rebuild_semantic_index()
        self.status_var.set(f"Imported {imported} verses from {Path(path).name}")

    def import_bible_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder of licensed Bible files")
        if not folder:
            return
        try:
            records = list(parse_bible_folder(folder))
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        imported = self.db.bulk_import(records)
        self.rebuild_semantic_index()
        self.status_var.set(f"Imported {imported} verses from folder")

    def import_strongs_file(self) -> None:
        path = filedialog.askopenfilename(title="Select Strong's file", filetypes=[("Lexicon Files", "*.csv *.jsonl"), ("All Files", "*.*")])
        if not path:
            return
        fmt = self.lexicon_format_var.get().strip().lower()
        fmt = None if fmt == "auto" else fmt
        try:
            entries = list(parse_strongs_file(path, fmt=fmt))
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        imported = self.db.bulk_import_strongs(entries)
        self.status_var.set(f"Imported {imported} Strong's entries from {Path(path).name}")

    def prev_verse(self) -> None:
        try:
            book = self.normalize_current_book()
            chapter = int(self.chapter_var.get() or 1)
            verse = int(self.verse_var.get() or 1)
        except Exception:
            return

        if verse > 1:
            self.verse_var.set(verse - 1)
            self.display_current_verse()
            return

        prev_chapter = chapter - 1
        if prev_chapter < 1:
            return

        try:
            verses = self.db.get_chapter(self.translation_var.get(), book, prev_chapter)
        except Exception:
            verses = []

        if not verses:
            return

        self.chapter_var.set(prev_chapter)
        self.verse_var.set(max(v.verse for v in verses))
        self.display_current_verse()

    def next_verse(self) -> None:
        try:
            book = self.normalize_current_book()
            chapter = int(self.chapter_var.get() or 1)
            verse = int(self.verse_var.get() or 1)
        except Exception:
            return

        try:
            verses = self.db.get_chapter(self.translation_var.get(), book, chapter)
        except Exception:
            verses = []

        max_verse = max((v.verse for v in verses), default=verse)
        if verse < max_verse:
            self.verse_var.set(verse + 1)
            self.display_current_verse()
            return

        next_chapter = chapter + 1
        try:
            next_verses = self.db.get_chapter(self.translation_var.get(), book, next_chapter)
        except Exception:
            next_verses = []

        if not next_verses:
            return

        self.chapter_var.set(next_chapter)
        self.verse_var.set(1)
        self.display_current_verse()

    def read_current_chapter(self):
        translation = self.translation_var.get().strip().lower()
        book = self.normalize_current_book()
        chapter = int(self.chapter_var.get())
        verses = self.db.get_chapter(translation, book, chapter)
        self.reader.delete("1.0", "end")
        self.reader.insert("end", f"{translation.upper()} {book.title()} {chapter}\n\n")
        for verse in verses:
            self.reader.insert("end", f"{verse.verse}. {self.sanitize_display_text(verse.text)}\n\n")
