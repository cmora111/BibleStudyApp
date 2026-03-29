from __future__ import annotations

import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import webbrowser

from app.core.bible_db import BibleDB
from app.core.book_normalizer import normalize_book_name
from app.core.config import DB_FILE
from app.core.importers import parse_bible_file, parse_bible_folder, parse_strongs_file
from app.core.utils import pretty_ref
from app.engines.commentary import CommentaryEngine
from app.engines.knowledge_graph import KnowledgeGraphEngine
from app.engines.semantic_search import SemanticSearchEngine
from app.engines.strongs_engine import StrongsWordStudyEngine
from app.engines.study_assistant import AIBibleStudyAssistant
from app.engines.topic_engine import TopicEngine

try:
    from app.engines.scholar_alignment import ScholarAlignmentEngine
    from app.engines.scholar_search import ScholarSearchEngine
except Exception:
    ScholarAlignmentEngine = None
    ScholarSearchEngine = None


class UltimateBibleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ultimate Bible App v8.2")
        self.root.geometry("1480x940")

        self.db = BibleDB()
        self.topic_engine = TopicEngine()
        self.commentary_engine = CommentaryEngine()
        self.translation_var = tk.StringVar(value=self.default_translation())
        self.semantic_engine = SemanticSearchEngine(self.db, translation=self.translation_var.get())
        self.strongs_engine = StrongsWordStudyEngine(self.db, translation=self.translation_var.get())
        self.study_assistant = AIBibleStudyAssistant(self.semantic_engine, self.strongs_engine)
        self.graph_engine = KnowledgeGraphEngine()

        self.scholar_alignment = ScholarAlignmentEngine(DB_FILE) if ScholarAlignmentEngine else None
        self.scholar_search = ScholarSearchEngine(DB_FILE) if ScholarSearchEngine else None

        self.book_var = tk.StringVar(value="john")
        self.chapter_var = tk.IntVar(value=3)
        self.verse_var = tk.IntVar(value=16)
        self.status_var = tk.StringVar(value="Ready")
        self.strongs_query_var = tk.StringVar(value="G26")
        self.scholar_query_var = tk.StringVar(value="strongs:G25")
        self.import_translation_var = tk.StringVar(value="")
        self.import_format_var = tk.StringVar(value="auto")
        self.lexicon_format_var = tk.StringVar(value="auto")

        self.build_ui()
        self.display_current_verse()

    def default_translation(self):
        translations = self.db.translations()
        return translations[0] if translations else "kjv"

    def _known_books(self, translation: str) -> list[str]:
        if hasattr(self.db, "books"):
            try:
                return list(self.db.books(translation))
            except Exception:
                return []
        return []

    def normalize_current_book(self) -> str:
        translation = self.translation_var.get().strip().lower()
        raw_book = self.book_var.get().strip()
        book = normalize_book_name(raw_book, known_books=self._known_books(translation))
        self.book_var.set(book)
        return book

    def build_ui(self) -> None:
        self.build_menu()
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, width=320)
        center = ttk.Frame(main)
        right = ttk.Frame(main, width=420)
        main.add(left, weight=1)
        main.add(center, weight=4)
        main.add(right, weight=2)

        self.build_left_panel(left)
        self.build_center_panel(center)
        self.build_right_panel(right)
        ttk.Label(self.root, textvariable=self.status_var, anchor="w").pack(fill="x", padx=6, pady=4)

    def build_menu(self) -> None:
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        tools_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        menu.add_cascade(label="Tools", menu=tools_menu)

        file_menu.add_command(label="Import Bible File", command=self.import_bible)
        file_menu.add_command(label="Import Bible Folder", command=self.import_bible_folder)
        file_menu.add_command(label="Import Strong's Lexicon", command=self.import_strongs_file)
        file_menu.add_separator()
        file_menu.add_command(label="Rebuild Semantic Index", command=self.rebuild_semantic_index)
        file_menu.add_command(label="Exit", command=self.root.destroy)

        tools_menu.add_command(label="Semantic Search", command=self.run_semantic_search)
        tools_menu.add_command(label="AI Study Assistant", command=self.run_ai_assistant)
        tools_menu.add_command(label="Strong's Word Study", command=self.run_strongs_lookup)
        tools_menu.add_command(label="Scholar Search", command=self.run_scholar_search)
        tools_menu.add_command(label="Generate Commentary", command=self.generate_commentary)
        tools_menu.add_command(label="Export Knowledge Graph", command=self.export_graph)

    def build_left_panel(self, parent: ttk.Frame) -> None:
        controls = ttk.LabelFrame(parent, text="Navigation")
        controls.pack(fill="x", padx=8, pady=8)

        ttk.Label(controls, text="Translation").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.translation_combo = ttk.Combobox(controls, textvariable=self.translation_var, values=self.db.translations() or ["kjv"], state="readonly")
        self.translation_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self.translation_combo.bind("<<ComboboxSelected>>", lambda e: self.on_translation_change())

        ttk.Label(controls, text="Book").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(controls, textvariable=self.book_var).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(controls, text="Chapter").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(controls, textvariable=self.chapter_var).grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(controls, text="Verse").grid(row=3, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(controls, textvariable=self.verse_var).grid(row=3, column=1, sticky="ew", padx=4, pady=4)

        ttk.Button(controls, text="Go", command=self.display_current_verse).grid(row=4, column=0, padx=4, pady=6, sticky="ew")
        ttk.Button(controls, text="Prev", command=self.prev_verse).grid(row=4, column=1, padx=4, pady=6, sticky="ew")
        ttk.Button(controls, text="Next", command=self.next_verse).grid(row=5, column=0, padx=4, pady=6, sticky="ew")
        ttk.Button(controls, text="Read Chapter", command=self.read_current_chapter).grid(row=5, column=1, padx=4, pady=6, sticky="ew")
        ttk.Button(controls, text="Commentary", command=self.generate_commentary).grid(row=6, column=0, padx=4, pady=6, sticky="ew")
        ttk.Button(controls, text="AI Assistant", command=self.run_ai_assistant).grid(row=6, column=1, padx=4, pady=6, sticky="ew")
        controls.columnconfigure(1, weight=1)

        search_box = ttk.LabelFrame(parent, text="Semantic Search")
        search_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.search_entry = ttk.Entry(search_box)
        self.search_entry.pack(fill="x", padx=6, pady=6)
        ttk.Button(search_box, text="Search", command=self.run_semantic_search).pack(fill="x", padx=6, pady=4)
        self.search_results = tk.Text(search_box, height=18, wrap="word")
        self.search_results.pack(fill="both", expand=True, padx=6, pady=6)

    def build_center_panel(self, parent: ttk.Frame) -> None:
        verse_frame = ttk.LabelFrame(parent, text="Bible Reader")
        verse_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.reader = tk.Text(verse_frame, wrap="word", font=("TkDefaultFont", 11), width=120, cursor="xterm")
        self.reader.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(verse_frame, text="Tip: scholar tokens render first when alignment data exists; otherwise fallback Strong's links are used.").pack(anchor="w", padx=6, pady=(0, 6))

    def build_right_panel(self, parent: ttk.Frame) -> None:
        assistant_frame = ttk.LabelFrame(parent, text="AI Bible Study Assistant")
        assistant_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.question_entry = ttk.Entry(assistant_frame)
        self.question_entry.pack(fill="x", padx=6, pady=6)
        self.question_entry.insert(0, "What does the Bible teach about salvation?")
        ttk.Button(assistant_frame, text="Generate Study Guide", command=self.run_ai_assistant).pack(fill="x", padx=6, pady=4)
        self.assistant_output = tk.Text(assistant_frame, wrap="word", height=14)
        self.assistant_output.pack(fill="both", expand=True, padx=6, pady=6)

        commentary_frame = ttk.LabelFrame(parent, text="Commentary / Strong's")
        commentary_frame.pack(fill="both", expand=True, padx=8, pady=8)
        tools_row = ttk.Frame(commentary_frame)
        tools_row.pack(fill="x", padx=6, pady=4)
        ttk.Entry(tools_row, textvariable=self.strongs_query_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(tools_row, text="Strong's Lookup", command=self.run_strongs_lookup).pack(side="left")
        self.commentary_output = tk.Text(commentary_frame, wrap="word", height=10)
        self.commentary_output.pack(fill="both", expand=True, padx=6, pady=6)

        scholar_frame = ttk.LabelFrame(parent, text="Scholar Search")
        scholar_frame.pack(fill="both", expand=True, padx=8, pady=8)
        scholar_row = ttk.Frame(scholar_frame)
        scholar_row.pack(fill="x", padx=6, pady=4)
        ttk.Entry(scholar_row, textvariable=self.scholar_query_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(scholar_row, text="Run", command=self.run_scholar_search).pack(side="left")
        self.scholar_output = tk.Text(scholar_frame, wrap="word", height=10)
        self.scholar_output.pack(fill="both", expand=True, padx=6, pady=6)

        import_frame = ttk.LabelFrame(parent, text="Licensed Dataset Import")
        import_frame.pack(fill="x", padx=8, pady=8)
        ttk.Label(import_frame, text="Override translation (optional)").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(import_frame, textvariable=self.import_translation_var).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(import_frame, text="Bible format").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(import_frame, textvariable=self.import_format_var, values=["auto", "pipe", "csv", "jsonl"], state="readonly").grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(import_frame, text="Lexicon format").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(import_frame, textvariable=self.lexicon_format_var, values=["auto", "csv", "jsonl"], state="readonly").grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(import_frame, text="Import Bible File", command=self.import_bible).grid(row=3, column=0, sticky="ew", padx=4, pady=6)
        ttk.Button(import_frame, text="Import Bible Folder", command=self.import_bible_folder).grid(row=3, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(import_frame, text="Import Strong's File", command=self.import_strongs_file).grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        import_frame.columnconfigure(1, weight=1)

    def on_translation_change(self) -> None:
        self.semantic_engine.set_translation(self.translation_var.get())
        self.strongs_engine.set_translation(self.translation_var.get())
        self.display_current_verse()
        self.status_var.set(f"Switched to {self.translation_var.get().upper()}")

    def current_verse(self):
        return self.db.get_verse(self.translation_var.get(), self.normalize_current_book(), int(self.chapter_var.get()), int(self.verse_var.get()))

    def _insert_scholar_tokens(self, verse_obj) -> bool:
        if not self.scholar_alignment or not hasattr(self.scholar_alignment, "verse_tokens"):
            return False
        tokens = self.scholar_alignment.verse_tokens(verse_obj.translation.lower(), verse_obj.book.lower(), verse_obj.chapter, verse_obj.verse)
        if not tokens:
            return False
        for idx, tok in enumerate(tokens):
            token_text = getattr(tok, "token_text", getattr(tok, "token", ""))
            strongs_id = getattr(tok, "strongs_id", getattr(tok, "strongs", ""))
            start = self.reader.index("end-1c")
            self.reader.insert("end", token_text)
            end = self.reader.index("end-1c")
            if strongs_id:
                tag = f"scholar_{idx}_{strongs_id}_{start.replace('.', '_')}"
                self.reader.tag_add(tag, start, end)
                self.reader.tag_config(tag, foreground="#1d4ed8", underline=True)
                self.reader.tag_bind(tag, "<Button-1>", lambda e, c=strongs_id: self.open_strongs_code(c))
                self.reader.tag_bind(tag, "<Enter>", lambda e: self.reader.config(cursor="hand2"))
                self.reader.tag_bind(tag, "<Leave>", lambda e: self.reader.config(cursor="xterm"))
            self.reader.insert("end", " ")
        return True

    def _insert_clickable_words(self, verse_text: str, strongs_codes: str) -> None:
        verse_shim = type("VerseShim", (), {"text": verse_text, "strongs": strongs_codes})()
        linked_words = self.strongs_engine.extract_word_links(verse_shim)
        pieces = verse_text.split()
        for idx, piece in enumerate(pieces):
            clean = "".join(ch for ch in piece if ch.isalpha() or ch == "'")
            code = linked_words[idx][1] if idx < len(linked_words) else None
            start = self.reader.index("end-1c")
            self.reader.insert("end", piece)
            end = self.reader.index("end-1c")
            if code and clean:
                tag = f"strongs_{idx}_{code}_{start.replace('.', '_')}"
                self.reader.tag_add(tag, start, end)
                self.reader.tag_config(tag, foreground="#1d4ed8", underline=True)
                self.reader.tag_bind(tag, "<Button-1>", lambda e, c=code: self.open_strongs_code(c))
                self.reader.tag_bind(tag, "<Enter>", lambda e: self.reader.config(cursor="hand2"))
                self.reader.tag_bind(tag, "<Leave>", lambda e: self.reader.config(cursor="xterm"))
            if idx < len(pieces) - 1:
                self.reader.insert("end", " ")

    def insert_clickable_reference(self, widget, ref_text: str):
        tag_name = f"ref_{ref_text}_{widget.index('end').replace('.', '_')}"
        start = widget.index("end")
        widget.insert("end", ref_text)
        end = widget.index("end")
        widget.tag_add(tag_name, start, end)
        widget.tag_config(tag_name, foreground="blue", underline=True)
        widget.tag_bind(tag_name, "<Button-1>", lambda event, ref=ref_text: self.open_reference_from_string(ref))
        widget.tag_bind(tag_name, "<Enter>", lambda e: widget.config(cursor="hand2"))
        widget.tag_bind(tag_name, "<Leave>", lambda e: widget.config(cursor="xterm"))

    def insert_assistant_text_with_links(self, widget, text: str):
        pattern = re.compile(r'([1-3]?\s?[A-Za-z ]+\s+\d+:\d+)')
        pos = 0
        for match in pattern.finditer(text):
            start, end = match.span()
            widget.insert("end", text[pos:start])
            self.insert_clickable_reference(widget, match.group(1).strip())
            pos = end
        widget.insert("end", text[pos:])

    def display_current_verse(self) -> None:
        verse = self.current_verse()
        self.reader.delete("1.0", "end")
        if verse is None:
            self.reader.insert("end", "Verse not found in the database. Import Bible text or change the reference.")
            self.status_var.set("Verse not found")
            return
        context = self.db.get_context(verse.translation, verse.book, verse.chapter, verse.verse)
        self.reader.insert("end", f"{pretty_ref(verse.book, verse.chapter, verse.verse)} [{verse.translation.upper()}]\n\n")
        for row in context:
            self.reader.insert("end", f"{row.chapter}:{row.verse} ")
            if row.verse == verse.verse:
                if not self._insert_scholar_tokens(row):
                    self._insert_clickable_words(row.text, getattr(row, "strongs", ""))
            else:
                self.reader.insert("end", row.text)
            self.reader.insert("end", "\n\n")
        topics = self.topic_engine.detect(verse.text)
        if topics:
            self.reader.insert("end", f"Detected Topics: {', '.join(topics)}\n")
        self.status_var.set(f"Loaded {pretty_ref(verse.book, verse.chapter, verse.verse)}")

    def open_strongs_code(self, code: str) -> None:
        self.strongs_query_var.set(code)
        self.run_strongs_lookup()

    def prev_verse(self) -> None:
        self.verse_var.set(max(1, int(self.verse_var.get()) - 1))
        self.display_current_verse()

    def next_verse(self) -> None:
        self.verse_var.set(int(self.verse_var.get()) + 1)
        self.display_current_verse()

    def open_reference_with_context(self, translation: str, book: str, chapter: int, verse: int):
        verses = self.db.get_context(translation, book, chapter, verse)
        self.reader.delete("1.0", "end")
        if not verses:
            self.reader.insert("end", f"{translation.upper()} does not contain {book.title()} {chapter}:{verse}")
            return
        self.reader.insert("end", f"{translation.upper()} {book.title()} {chapter}:{verse}\n\n")
        for v in verses:
            prefix = "→ " if v.verse == verse else "  "
            self.reader.insert("end", f"{prefix}{v.chapter}:{v.verse} {v.text}\n\n")

    def rebuild_semantic_index(self) -> None:
        translation = self.translation_var.get().strip().lower()
        self.semantic_engine = SemanticSearchEngine(self.db, translation=translation)
        self.strongs_engine.set_translation(translation)
        self.study_assistant = AIBibleStudyAssistant(self.semantic_engine, self.strongs_engine)
        translations = self.db.translations() or ["kjv"]
        self.translation_combo.configure(values=translations)
        if self.translation_var.get() not in translations:
            self.translation_var.set(translations[0])

    def run_semantic_search(self) -> None:
        query = self.search_entry.get().strip()
        self.search_results.delete("1.0", "end")
        if not query:
            return
        hits = self.semantic_engine.search(query, limit=20)
        if not hits:
            self.search_results.insert("end", "No results.")
            return
        for hit in hits:
            ref = pretty_ref(hit.verse.book, hit.verse.chapter, hit.verse.verse)
            self.search_results.insert("end", f"{ref} [{hit.verse.translation.upper()}] score={hit.score:.3f}\n{hit.verse.text}\n\n")

    def run_ai_assistant(self) -> None:
        question = self.question_entry.get().strip()
        self.assistant_output.delete("1.0", "end")
        if not question:
            return
        try:
            answer = self.study_assistant.answer(question, translation=self.translation_var.get().strip().lower())
        except TypeError:
            answer = self.study_assistant.answer(question)
        self.assistant_output.insert("end", f"{answer.title}\n\n")
        self.assistant_output.insert("end", f"Summary\n{answer.summary}\n\n")
        self.assistant_output.insert("end", f"Detected Topics\n{', '.join(answer.detected_topics) if answer.detected_topics else 'None'}\n")
        self.assistant_output.insert("end", f"Semantic Engine\n{answer.semantic_engine_mode}\n\n")
        self.assistant_output.insert("end", "Key Passages\n")
        for item in answer.key_passages:
            self.assistant_output.insert("end", "- ")
            self.insert_assistant_text_with_links(self.assistant_output, str(item))
            self.assistant_output.insert("end", "\n")
        self.assistant_output.insert("end", "\nCross References\n")
        for item in answer.cross_references:
            self.assistant_output.insert("end", "- ")
            self.insert_assistant_text_with_links(self.assistant_output, str(item))
            self.assistant_output.insert("end", "\n")
        self.assistant_output.insert("end", "\nWord Study Hints\n")
        for item in answer.word_study:
            self.assistant_output.insert("end", f"- {item}\n")
        self.assistant_output.insert("end", "\nReflection Questions\n")
        for item in answer.reflection_questions:
            self.assistant_output.insert("end", f"- {item}\n")
        self.status_var.set("AI study guide generated")

    def generate_commentary(self) -> None:
        verse = self.current_verse()
        self.commentary_output.delete("1.0", "end")
        if verse is None:
            self.commentary_output.insert("end", "Verse not found.")
            return
        self.commentary_output.insert("end", self.commentary_engine.explain(verse))
        coded = [f"{word} ({code})" for word, code in self.strongs_engine.extract_word_links(verse) if code]
        if coded:
            self.commentary_output.insert("end", "\n\nStrong's-linked words\n")
            for item in coded[:15]:
                self.commentary_output.insert("end", f"- {item}\n")
        self.status_var.set("Commentary generated")

    def run_strongs_lookup(self) -> None:
        query = self.strongs_query_var.get().strip()
        self.commentary_output.delete("1.0", "end")
        if not query:
            return
        if query[:1].upper() in {"G", "H"} and query[1:].isdigit():
            result = self.strongs_engine.study_code(query)
            if result.entry is None:
                self.commentary_output.insert("end", f"No Strong's entry found for {query.upper()}.\n")
            else:
                entry = result.entry
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
            self.commentary_output.insert("end", f"{hit.strongs_id} — {hit.lemma} ({hit.transliteration})\n")
            self.commentary_output.insert("end", f"{hit.definition}\n\n")
        self.status_var.set(f"Strong's search complete: {len(hits)} hits")

    def run_scholar_search(self) -> None:
        self.scholar_output.delete("1.0", "end")
        if not self.scholar_search:
            self.scholar_output.insert("end", "Scholar engine is not installed.\n")
            return
        query = self.scholar_query_var.get().strip()
        if not query:
            return
        translation = self.translation_var.get().strip().lower()
        hits = self.scholar_search.search(query, translation=translation, limit=100)
        if not hits:
            self.scholar_output.insert("end", "No scholar hits found.\n")
            return
        for hit in hits:
            self.scholar_output.insert("end", f"{hit.reference} [{hit.translation.upper()}]\n")
            self.scholar_output.insert("end", f"token={hit.token_text} strongs={hit.strongs_id or '-'} lemma={hit.lemma or '-'} morph={hit.morph or '-'}\n")
            self.scholar_output.insert("end", f"source={hit.source_lang or '-'} {hit.source_surface or ''}\n\n")
        self.status_var.set(f"Scholar search complete: {len(hits)} hits")

    def export_graph(self) -> None:
        html_path = self.graph_engine.export_html()
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
        messagebox.showinfo("Import complete", f"Imported {imported} verses into the database.")

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
        messagebox.showinfo("Import complete", f"Imported {imported} verses from {folder}.")

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
        messagebox.showinfo("Import complete", f"Imported {imported} Strong's lexicon entries.")

    def open_chapter(self, book: str, chapter: int):
        translation = self.translation_var.get().strip().lower()
        verses = self.db.get_chapter(translation, book, chapter)
        self.reader.delete("1.0", "end")
        self.reader.insert("end", f"{translation.upper()} {book.title()} {chapter}\n\n")
        for verse in verses:
            self.reader.insert("end", f"{verse.verse}. {verse.text}\n\n")

    def read_current_chapter(self):
        self.open_chapter(self.normalize_current_book(), int(self.chapter_var.get()))

    def open_reference_from_string(self, ref_text: str):
        ref_text = ref_text.strip()
        m = re.match(r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)$", ref_text)
        if not m:
            return
        translation = self.translation_var.get().strip().lower()
        book = normalize_book_name(m.group(1).strip(), known_books=self._known_books(translation))
        self.open_reference_with_context(translation, book, int(m.group(2)), int(m.group(3)))
