from tkinter import messagebox
import re
from app.ui.dataset_manager_window import DatasetManagerWindow

def default_translation(self):
    translations = self.db.translations()
    if translations:
        return translations[0]
    return "kjv"

def read_current_chapter(self):
    book = self.book_var.get().strip().lower()
    chapter = int(self.chapter_var.get())
    translation = self.translation_var.get().strip().lower()
    verses = self.db.get_chapter(translation, book, chapter)
    if not verses:
        messagebox.showerror("Missing Chapter", f"{translation.upper()} does not contain {book.title()} {chapter}")
        return
    self.reader.delete("1.0", "end")
    self.reader.insert("end", f"{translation.upper()} {book.title()} {chapter}\n\n")
    for verse in verses:
        self.reader.insert("end", f"{verse.verse}. {verse.text}\n\n")

def insert_clickable_reference(self, widget, ref_text: str):
    tag_name = f"ref_{ref_text}_{widget.index('end').replace('.', '_')}"
    start = widget.index("end")
    widget.insert("end", ref_text)
    end = widget.index("end")
    widget.tag_add(tag_name, start, end)
    widget.tag_config(tag_name, foreground="blue", underline=True)
    def on_click(event, ref=ref_text):
        self.open_reference_from_string(ref)
    widget.tag_bind(tag_name, "<Button-1>", on_click)

def insert_assistant_text_with_links(self, widget, text: str):
    pattern = re.compile(r'([1-3]?\s?[A-Za-z ]+\s+\d+:\d+)')
    pos = 0
    for match in pattern.finditer(text):
        start, end = match.span()
        widget.insert("end", text[pos:start])
        ref = match.group(1).strip()
        self.insert_clickable_reference(widget, ref)
        pos = end
    widget.insert("end", text[pos:])

def open_reference_from_string(self, ref_text: str):
    ref_text = ref_text.strip()
    m = re.match(r"^([1-3]?\s?[A-Za-z ]+)\s+(\d+):(\d+)$", ref_text)
    if not m:
        return
    raw_book = m.group(1).strip().lower()
    chapter = int(m.group(2))
    verse = int(m.group(3))
    book_map = {
        "genesis":"genesis","exodus":"exodus","leviticus":"leviticus","numbers":"numbers","deuteronomy":"deuteronomy",
        "joshua":"joshua","judges":"judges","ruth":"ruth","1 samuel":"1samuel","2 samuel":"2samuel",
        "1 kings":"1kings","2 kings":"2kings","1 chronicles":"1chronicles","2 chronicles":"2chronicles",
        "ezra":"ezra","nehemiah":"nehemiah","esther":"esther","job":"job","psalms":"psalms","proverbs":"proverbs",
        "ecclesiastes":"ecclesiastes","song of solomon":"songofsolomon","isaiah":"isaiah","jeremiah":"jeremiah",
        "lamentations":"lamentations","ezekiel":"ezekiel","daniel":"daniel","hosea":"hosea","joel":"joel","amos":"amos",
        "obadiah":"obadiah","jonah":"jonah","micah":"micah","nahum":"nahum","habakkuk":"habakkuk","zephaniah":"zephaniah",
        "haggai":"haggai","zechariah":"zechariah","malachi":"malachi","matthew":"matthew","mark":"mark","luke":"luke",
        "john":"john","acts":"acts","romans":"romans","1 corinthians":"1corinthians","2 corinthians":"2corinthians",
        "galatians":"galatians","ephesians":"ephesians","philippians":"philippians","colossians":"colossians",
        "1 thessalonians":"1thessalonians","2 thessalonians":"2thessalonians","1 timothy":"1timothy","2 timothy":"2timothy",
        "titus":"titus","philemon":"philemon","hebrews":"hebrews","james":"james","1 peter":"1peter","2 peter":"2peter",
        "1 john":"1john","2 john":"2john","3 john":"3john","jude":"jude","revelation":"revelation",
    }
    book = book_map.get(raw_book)
    if not book:
        return
    translation = self.translation_var.get().strip().lower()
    self.open_reference_with_context(translation, book, chapter, verse)

def open_reference_with_context(self, translation: str, book: str, chapter: int, verse: int):
    verses = self.db.get_context(translation, book, chapter, verse)
    if not verses:
        messagebox.showerror("Missing Verse", f"{translation.upper()} does not contain {book.title()} {chapter}:{verse}")
        return
    self.reader.delete("1.0", "end")
    self.reader.insert("end", f"{translation.upper()} {book.title()} {chapter}:{verse}\n\n")
    for v in verses:
        prefix = "→ " if v.verse == verse else "  "
        self.reader.insert("end", f"{prefix}{v.chapter}:{v.verse} {v.text}\n\n")

def open_dataset_manager(self):
    DatasetManagerWindow(self.root)
