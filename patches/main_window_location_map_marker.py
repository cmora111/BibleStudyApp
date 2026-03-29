from __future__ import annotations

import re
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import webbrowser

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

        self.semantic_engine = SemanticSearchEngine(self.db, translation=self.translation_var.get())
        self.strongs_engine = StrongsWordStudyEngine(self.db, translation=self.translation_var.get())
        self.study_assistant = AIBibleStudyAssistant(self.semantic_engine, self.strongs_engine)
        self.crossref_engine = CrossReferenceEngine() if CrossReferenceEngine else None
        self.timeline_engine = BibleTimelineEngine("data/timeline_events.csv")
        self.map_engine = BibleMapEngine("data/timeline_events.csv")
        self.event_graph_bridge = EventGraphBridge("data/timeline_events.csv")

        self.build_ui()
        self.root.after(100, self.display_current_verse)

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
        file_menu.add_command(label="Exit", command=self.root.destroy)
        tools_menu.add_command(label="Semantic Search", command=self.run_semantic_search)
        tools_menu.add_command(label="Generate Study Guide", command=self.run_ai_assistant)
        tools_menu.add_command(label="Strong's Word Study", command=self.run_strongs_lookup)
        tools_menu.add_command(label="Generate Commentary", command=self.generate_commentary)
        tools_menu.add_command(label="Export Knowledge Graph", command=self.export_graph)

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
        self.right_notebook = ttk.Notebook(parent, width=360)
        self.right_notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.study_tab = ttk.Frame(self.right_notebook, width=360)
        self.crossrefs_tab = ttk.Frame(self.right_notebook, width=360)
        self.compare_tab = ttk.Frame(self.right_notebook, width=360)
        self.commentary_tab = ttk.Frame(self.right_notebook, width=360)
        self.import_tab = ttk.Frame(self.right_notebook, width=360)
        self.timeline_tab = ttk.Frame(self.right_notebook, width=360)

        self.right_notebook.add(self.study_tab, text="Study Guide")
        self.right_notebook.add(self.crossrefs_tab, text="Cross Refs")
        self.right_notebook.add(self.compare_tab, text="Compare")
        self.right_notebook.add(self.commentary_tab, text="Commentary/Strong's")
        self.right_notebook.add(self.timeline_tab, text="Timeline / Map")
        self.right_notebook.add(self.import_tab, text="Import")

        self.build_study_tab(self.study_tab)
        self.build_crossrefs_tab(self.crossrefs_tab)
        self.build_compare_tab(self.compare_tab)
        self.build_commentary_tab(self.commentary_tab)
        self.build_timeline_tab(self.timeline_tab)
        self.build_import_tab(self.import_tab)

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

    def build_timeline_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Bible Timeline + Map")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        controls = ttk.Frame(frame)
        controls.pack(fill="x", padx=6, pady=6)

        self.timeline_filter_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=self.timeline_filter_var).pack(side="left", fill="x", expand=True)
        ttk.Button(controls, text="Filter", command=self.refresh_timeline_panel).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Current Book", command=self.filter_timeline_current_book).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Open Map", command=self.open_timeline_map).pack(side="left", padx=(6, 0))

        self.timeline_list = tk.Listbox(frame, height=16)
        self.timeline_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.timeline_list.bind("<<ListboxSelect>>", lambda e: self.on_timeline_select())

        details = ttk.LabelFrame(frame, text="Event Details")
        details.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.timeline_details = tk.Text(details, wrap="word", height=12)
        self.timeline_details.pack(fill="both", expand=True, padx=6, pady=6)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(buttons, text="Open Event in Reader", command=self.open_selected_timeline_event_in_reader).pack(side="left")
        ttk.Button(buttons, text="Search Event", command=self.search_selected_timeline_event).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Show Graph Links", command=self.show_selected_timeline_graph_links).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Show Location on Map", command=self.open_selected_timeline_location_on_map).pack(side="left", padx=(6, 0))

        self._timeline_events_cache = []
        self.refresh_timeline_panel()

    def build_commentary_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Commentary / Strong's")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        top = ttk.Frame(frame)
        top.pack(fill="x", padx=6, pady=4)
        ttk.Entry(top, textvariable=self.strongs_query_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(top, text="Strong's Lookup", command=self.run_strongs_lookup).pack(side="left")
        ttk.Button(top, text="Commentary", command=self.generate_commentary).pack(side="left", padx=(6, 0))
        self.commentary_output = tk.Text(frame, wrap="word", height=20)
        self.commentary_output.pack(fill="both", expand=True, padx=6, pady=6)

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
        mapping = {"genesis":"genesis","exodus":"exodus","leviticus":"leviticus","numbers":"numbers","deuteronomy":"deuteronomy","joshua":"joshua","judges":"judges","ruth":"ruth","1 samuel":"1samuel","2 samuel":"2samuel","1 kings":"1kings","2 kings":"2kings","1 chronicles":"1chronicles","2 chronicles":"2chronicles","ezra":"ezra","nehemiah":"nehemiah","esther":"esther","job":"job","psalm":"psalms","psalms":"psalms","proverbs":"proverbs","ecclesiastes":"ecclesiastes","song of solomon":"songofsolomon","song":"songofsolomon","isaiah":"isaiah","jeremiah":"jeremiah","lamentations":"lamentations","ezekiel":"ezekiel","daniel":"daniel","hosea":"hosea","joel":"joel","amos":"amos","obadiah":"obadiah","jonah":"jonah","micah":"micah","nahum":"nahum","habakkuk":"habakkuk","zephaniah":"zephaniah","haggai":"haggai","zechariah":"zechariah","malachi":"malachi","matthew":"matthew","mark":"mark","luke":"luke","john":"john","acts":"acts","romans":"romans","1 corinthians":"1corinthians","2 corinthians":"2corinthians","galatians":"galatians","ephesians":"ephesians","philippians":"philippians","colossians":"colossians","1 thessalonians":"1thessalonians","2 thessalonians":"2thessalonians","1 timothy":"1timothy","2 timothy":"2timothy","titus":"titus","philemon":"philemon","hebrews":"hebrews","james":"james","1 peter":"1peter","2 peter":"2peter","1 john":"1john","2 john":"2john","3 john":"3john","jude":"jude","revelation":"revelation"}
        return mapping.get(raw, raw.replace(" ", ""))

    def normalize_current_book(self) -> str:
        return self.normalize_book_name(self.book_var.get())

    def current_verse(self):
        return self.db.get_verse(self.translation_var.get(), self.normalize_current_book(), int(self.chapter_var.get()), int(self.verse_var.get()))

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
                self.reader.tag_config(tag, foreground="#2563eb", underline=True)
                self.reader.tag_bind(tag, "<Button-1>", lambda e, c=strongs: self.open_strongs_code(str(c)))
                self.reader.tag_bind(tag, "<Enter>", lambda e: self.reader.config(cursor="hand2"))
                self.reader.tag_bind(tag, "<Leave>", lambda e: self.reader.config(cursor="xterm"))

            if i < len(words):
                self.reader.insert("end", " ")

    def display_current_verse(self, startup: bool = False) -> None:
        verse = self.current_verse()
        self.reader.delete("1.0", "end")
        if verse is None:
            self.reader.insert("end", "Verse not found in the database. Import Bible text or change the reference.")
            self.status_var.set("Verse not found")
            self.refresh_crossrefs_panel()
            self.refresh_compare_panel()
            return

        context = self.db.get_context(verse.translation, verse.book, verse.chapter, verse.verse)
        # Formatting engine lock: verse text is normalized before insertion.
        self.reader.insert("end", f"{pretty_ref(verse.book, verse.chapter, verse.verse)} [{verse.translation.upper()}]\n\n")
        for row in context:
            self.reader.insert("end", f"{row.chapter}:{row.verse} ")
            if row.verse == verse.verse:
                self._insert_clickable_words(row.text, "", verse=row)
            else:
                self.reader.insert("end", self.sanitize_display_text(row.text))
            self.reader.insert("end", "\n\n")

        topics = self.topic_engine.detect(verse.text)
        if topics:
            self.reader.insert("end", "\nDetected Topics:\n")
            for idx, topic in enumerate(topics):
                start = self.reader.index("end-1c")
                label = topic
                self.reader.insert("end", label)
                end = self.reader.index(f"{start} + {len(label)}c")
                tag = f"reader_topic_{idx}_{topic}"
                self.reader.tag_add(tag, start, end)
                self.reader.tag_config(tag, foreground="#1a73e8", underline=True)
                self.reader.tag_bind(tag, "<Button-1>", lambda e, q=topic: self.run_semantic_search_for_query(q))
                self.reader.tag_bind(tag, "<Enter>", lambda e: self.reader.config(cursor="hand2"))
                self.reader.tag_bind(tag, "<Leave>", lambda e: self.reader.config(cursor="xterm"))
                if idx < len(topics) - 1:
                    self.reader.insert("end", ", ")
                else:
                    self.reader.insert("end", "\n")
            try:
                self.search_entry.delete(0, "end")
                self.search_entry.insert(0, " ".join(topics[:5]))
            except Exception:
                pass

        clickable = self.build_top_clickable_strongs_list(verse.book, verse.chapter, verse.verse, verse.translation)
        if clickable:
            self.reader.insert("end", "\nClickable Strong's Links:\n")
            for idx, (word, code) in enumerate(clickable[:20]):
                start = self.reader.index("end-1c")
                label = f"{word} ({code})"
                self.reader.insert("end", label)
                end = self.reader.index(f"{start} + {len(label)}c")
                tag = f"top_strongs_{idx}_{code}"
                self.reader.tag_add(tag, start, end)
                self.reader.tag_config(tag, foreground="#1d4ed8", underline=True)
                self.reader.tag_bind(tag, "<Button-1>", lambda e, c=code: self.open_strongs_code(str(c)))
                self.reader.tag_bind(tag, "<Enter>", lambda e: self.reader.config(cursor="hand2"))
                self.reader.tag_bind(tag, "<Leave>", lambda e: self.reader.config(cursor="xterm"))
                if idx < min(len(clickable), 20) - 1:
                    self.reader.insert("end", "  •  ")
                else:
                    self.reader.insert("end", "\n")
        else:
            self.reader.insert("end", "\n(No Strong's data for this translation)\n")

        self.update_semantic_topics_panel(topics)
        self.status_var.set(f"Loaded {pretty_ref(verse.book, verse.chapter, verse.verse)}")
        self.refresh_crossrefs_panel()
        self.refresh_compare_panel()
        try:
            self.filter_timeline_current_book()
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
            row = self.db.get_verse(tr, book, chapter, verse)
            if row:
                self.compare_output.insert("end", f"[{tr.upper()}] {row.text}\n\n")
            else:
                self.compare_output.insert("end", f"[{tr.upper()}] Verse not available\n\n")

    def get_crossref_preview_rows_for_current(self):
        rows = []
        if self.crossref_engine:
            try:
                refs = self.crossref_engine.get_cross_references(self.normalize_current_book(), int(self.chapter_var.get()), int(self.verse_var.get()), limit=50)
            except Exception:
                refs = []
            for r in refs:
                ref_label = f"{r.target_book.title()} {r.target_chapter}:{r.target_verse}"
                preview_text = self.fetch_verse_text(r.target_book, r.target_chapter, r.target_verse, translation=self.translation_var.get().strip().lower()) or self.fetch_verse_text(r.target_book, r.target_chapter, r.target_verse, translation="esv")
                rows.append({"ref": ref_label, "votes": r.votes, "text": preview_text or "(verse text unavailable)"})
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
            self.assistant_output.insert("end", f"• {item}\n\n")
            end = self.assistant_output.index("end-1c")
            tag = f"study_passage_{idx}"
            self.assistant_output.tag_add(tag, start, end)
            self.assistant_output.tag_config(tag, foreground="#1a73e8", underline=True)
            self.assistant_output.tag_bind(tag, "<Button-1>", lambda e, ref=item: self.open_study_passage_popup(ref))

        self.assistant_output.insert("end", "Cross References\n\n")
        for idx, item in enumerate(answer.cross_references):
            start = self.assistant_output.index("end-1c")
            self.assistant_output.insert("end", f"• {item}\n\n")
            end = self.assistant_output.index("end-1c")
            tag = f"study_xref_{idx}"
            self.assistant_output.tag_add(tag, start, end)
            self.assistant_output.tag_config(tag, foreground="#1a73e8", underline=True)
            self.assistant_output.tag_bind(tag, "<Button-1>", lambda e, ref=item: self.open_study_passage_popup(ref))

        self.assistant_output.insert("end", "Reflection Questions\n\n")
        for item in answer.reflection_questions:
            self.assistant_output.insert("end", f"• {item}\n\n")

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
        query = getattr(self, "timeline_filter_var", None)
        q = query.get().strip() if query else ""
        try:
            events = self.timeline_engine.search_events(q) if q else self.timeline_engine.get_all_events()
        except Exception as exc:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", f"Timeline engine error: {exc}")
            return

        self._timeline_events_cache = events
        self.timeline_list.delete(0, "end")
        for event in events:
            year = event.time_label or "Unknown time"
            self.timeline_list.insert("end", f"{event.title} — {year}")

        if events:
            self.timeline_list.selection_clear(0, "end")
            self.timeline_list.selection_set(0)
            self.on_timeline_select()
        else:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", "No timeline events found.")

    def filter_timeline_current_book(self):
        try:
            self.timeline_filter_var.set(self.normalize_current_book())
        except Exception:
            self.timeline_filter_var.set("")
        self.refresh_timeline_panel()

    def on_timeline_select(self):
        if not getattr(self, "_timeline_events_cache", None):
            return
        selection = self.timeline_list.curselection()
        if not selection:
            return
        event = self._timeline_events_cache[selection[0]]

        self.timeline_details.delete("1.0", "end")
        self.timeline_details.insert("end", f"{event.title}\n\n")
        self.timeline_details.insert("end", f"Reference: {event.reference}\n")
        self.timeline_details.insert("end", "Use \"Open Event in Reader\" to sync the Reader, Compare, Cross Refs, and Semantic Search.\n")
        self.timeline_details.insert("end", f"Time: {event.time_label or 'Unknown'}\n")

        self.timeline_details.insert("end", "Location: ")
        loc_value_start = self.timeline_details.index("end-1c")
        self.timeline_details.insert("end", f"{event.location_name or 'Unknown'}")
        loc_value_end = self.timeline_details.index("end-1c")
        self.timeline_details.insert("end", "\n")

        if event.location_name and event.latitude is not None and event.longitude is not None:
            tag = "timeline_location_link"
            self.timeline_details.tag_add(tag, loc_value_start, loc_value_end)
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

    def open_selected_timeline_event_in_reader(self):
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return

        event = self._timeline_events_cache[selection[0]]

        self.book_var.set(event.book)
        self.chapter_var.set(event.chapter_start)
        self.verse_var.set(event.verse_start)

        self.display_current_verse()

        try:
            self.refresh_crossrefs_panel()
            self.refresh_compare_panel()
            self.run_semantic_search_for_query(event.title)
        except Exception:
            pass

        try:
            self.right_notebook.select(self.compare_tab)
        except Exception:
            pass

    def open_selected_timeline_location_on_map(self):
        selection = self.timeline_list.curselection()
        if not selection or not getattr(self, "_timeline_events_cache", None):
            return

        event = self._timeline_events_cache[selection[0]]
        if event.latitude is None or event.longitude is None:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", "This event does not have map coordinates.")
            return

        try:
            output = self.map_engine.export_single_event_map(
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
        nodes, edges = self.event_graph_bridge.event_to_graph_bundle(event.id)
        self.timeline_details.delete("1.0", "end")
        lines = [event.title, "", "Graph Nodes:"]
        for node in nodes:
            lines.append(f"- {node.node_type}: {node.label}")
        lines.append("")
        lines.append("Graph Edges:")
        for edge in edges:
            lines.append(f"- {edge.source} -> {edge.target} ({edge.relation})")
        self.timeline_details.insert("1.0", "\n".join(lines))

    def open_timeline_map(self):
        try:
            output = self.map_engine.export_map("exports/bible_timeline_map.html")
        except Exception as exc:
            self.timeline_details.delete("1.0", "end")
            self.timeline_details.insert("end", f"Map export failed: {exc}")
            return
        self.timeline_details.delete("1.0", "end")
        self.timeline_details.insert("end", f"Map exported to:\n{output}")
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
        self.run_semantic_search_for_query(event.title)

    def on_translation_change(self) -> None:
        self.semantic_engine.set_translation(self.translation_var.get())
        self.strongs_engine.set_translation(self.translation_var.get())
        self.display_current_verse()
        self.status_var.set(f"Switched to {self.translation_var.get().upper()}")

    def prev_verse(self) -> None:
        self.verse_var.set(max(1, int(self.verse_var.get()) - 1))
        self.display_current_verse()

    def next_verse(self) -> None:
        self.verse_var.set(int(self.verse_var.get()) + 1)
        self.display_current_verse()

    def rebuild_semantic_index(self) -> None:
        self.semantic_engine = SemanticSearchEngine(self.db, translation=self.translation_var.get())
        self.strongs_engine.set_translation(self.translation_var.get())
        self.study_assistant = AIBibleStudyAssistant(self.semantic_engine, self.strongs_engine)
        translations = self.db.translations() or ["kjv"]
        self.translation_combo.configure(values=translations)
        if self.translation_var.get() not in translations:
            self.translation_var.set(translations[0])
        self.status_var.set(f"Semantic index rebuilt ({self.semantic_engine.mode})")

    def run_semantic_search_for_query(self, query: str):
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, query)
        self.run_semantic_search()

    def run_semantic_search(self) -> None:
        query = self.search_entry.get().strip()
        self.search_results.delete("1.0", "end")
        if not query:
            return
        hits = self.semantic_engine.search(query, limit=20)
        if not hits:
            self.search_results.insert("end", "No results. Import more Bible text or broaden the query.")
            return
        self.search_results.insert("end", f"Semantic engine mode: {self.semantic_engine.mode}\n\n")
        for idx, hit in enumerate(hits):
            ref = pretty_ref(hit.verse.book, hit.verse.chapter, hit.verse.verse)
            header = f"{ref} [{hit.verse.translation.upper()}]  score={hit.score:.3f}"
            start = self.search_results.index("end-1c")
            self.search_results.insert("end", header + "\n")
            end = self.search_results.index("end-1c")
            tag = f"search_ref_{idx}"
            self.search_results.tag_add(tag, start, end)
            self.search_results.tag_config(tag, foreground="#1a73e8", underline=True)
            self.search_results.tag_bind(tag, "<Button-1>", lambda e, h=hit: self.open_semantic_result_popup(h))
            self.search_results.insert("end", f"{hit.verse.text}\n\n")
        self.status_var.set(f"Semantic search complete: {len(hits)} results ({self.semantic_engine.mode})")

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
        answer = self.study_assistant.answer(question)
        self.render_study_guide(answer)
        self.build_study_question_buttons(answer)
        self.status_var.set("Study guide generated")

    def generate_commentary(self) -> None:
        verse = self.current_verse()
        self.commentary_output.delete("1.0", "end")
        if verse is None:
            self.commentary_output.insert("end", "Verse not found.")
            return
        self.commentary_output.insert("end", self.commentary_engine.explain(verse))
        links = self.build_top_clickable_strongs_list(verse.book, verse.chapter, verse.verse, verse.translation)
        if links:
            self.commentary_output.insert("end", "\n\nWord / Strong's Links\n")
            for word, code in links[:15]:
                self.commentary_output.insert("end", f"- {word} — {code}\n")
        self.status_var.set("Commentary generated")

    def open_strongs_code(self, code: str) -> None:
        self.strongs_query_var.set(str(code))
        try:
            self.right_notebook.select(self.commentary_tab)
        except Exception:
            pass
        self.run_strongs_lookup()

    def run_strongs_lookup(self) -> None:
        query = self.strongs_query_var.get().strip()
        self.commentary_output.delete("1.0", "end")
        if not query:
            return
        verse = self.current_verse()
        word_map = self.build_top_clickable_strongs_list(verse.book, verse.chapter, verse.verse, verse.translation) if verse else []
        if query[:1].upper() in {"G", "H"} and query[1:].isdigit():
            result = self.strongs_engine.study_code(query)
            if result.entry is None:
                self.commentary_output.insert("end", f"No Strong's entry found for {query.upper()}.\n")
            else:
                entry = result.entry
                matching_words = [w for w, c in word_map if c.upper() == query.upper()]
                if matching_words:
                    self.commentary_output.insert("end", f"Word(s): {', '.join(sorted(set(matching_words)))}\n")
                self.commentary_output.insert("end", f"{entry.strongs_id} — {entry.lemma}\n")
                self.commentary_output.insert("end", f"Transliteration: {entry.transliteration or 'N/A'}\n")
                self.commentary_output.insert("end", f"Language: {entry.language}\n")
                self.commentary_output.insert("end", f"Gloss: {entry.gloss or 'N/A'}\n\n")
                self.commentary_output.insert("end", f"Definition\n{entry.definition}\n\n")
                self.commentary_output.insert("end", "Occurrences\n")
                for occ in result.occurrences:
                    self.commentary_output.insert("end", f"- {occ}\n")
            self.status_var.set(f"Strong's lookup complete: {query.upper()}")
            return
        hits = self.strongs_engine.search(query)
        if not hits:
            self.commentary_output.insert("end", f"No Strong's entries found for '{query}'.")
            self.status_var.set("No Strong's matches")
            return
        self.commentary_output.insert("end", f"Strong's search results for '{query}'\n\n")
        for hit in hits:
            linked_words = [w for w, c in word_map if c.upper() == hit.strongs_id.upper()]
            if linked_words:
                self.commentary_output.insert("end", f"Word(s): {', '.join(sorted(set(linked_words)))}\n")
            self.commentary_output.insert("end", f"{hit.strongs_id} — {hit.lemma} ({hit.transliteration})\n")
            self.commentary_output.insert("end", f"{hit.definition}\n\n")
        self.status_var.set(f"Strong's search complete: {len(hits)} hits")

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

    def read_current_chapter(self):
        translation = self.translation_var.get().strip().lower()
        book = self.normalize_current_book()
        chapter = int(self.chapter_var.get())
        verses = self.db.get_chapter(translation, book, chapter)
        self.reader.delete("1.0", "end")
        self.reader.insert("end", f"{translation.upper()} {book.title()} {chapter}\n\n")
        for verse in verses:
            self.reader.insert("end", f"{verse.verse}. {self.sanitize_display_text(verse.text)}\n\n")