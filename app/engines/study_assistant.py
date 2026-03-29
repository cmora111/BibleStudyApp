from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Compatibility constant expected by knowledge_graph.py.
# Keep this available even if your app later switches to DB-backed cross references.
CROSS_REFERENCES: dict[str, list[str]] = {
    "John 3:16": ["Romans 5:8", "1 John 4:9", "Ephesians 2:8"],
    "Romans 8:28": ["Genesis 50:20", "James 1:2", "1 Peter 5:10"],
    "Hebrews 11:1": ["Romans 10:17", "2 Corinthians 5:7"],
    "Genesis 1:1": ["John 1:1", "Colossians 1:16", "Hebrews 11:3"],
}


@dataclass(slots=True)
class StudyAssistantAnswer:
    title: str
    summary: str
    detected_topics: list[str] = field(default_factory=list)
    semantic_engine_mode: str = "unknown"
    key_passages: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    word_study: list[str] = field(default_factory=list)
    reflection_questions: list[str] = field(default_factory=list)


class AIBibleStudyAssistant:
    """
    Offline Bible study assistant that accepts a selected translation and
    keeps searches constrained to that translation when supported.
    """

    def __init__(self, semantic_engine: Any, strongs_engine: Any):
        self.semantic_engine = semantic_engine
        self.strongs_engine = strongs_engine
        self.db = getattr(semantic_engine, "db", None)

    def _set_translation_if_supported(self, translation: str | None) -> None:
        if not translation:
            return
        if hasattr(self.semantic_engine, "set_translation"):
            self.semantic_engine.set_translation(translation)
        if hasattr(self.strongs_engine, "set_translation"):
            self.strongs_engine.set_translation(translation)

    def _semantic_hits(self, question: str, translation: str | None, limit: int = 8):
        self._set_translation_if_supported(translation)
        if hasattr(self.semantic_engine, "search"):
            try:
                return self.semantic_engine.search(question, limit=limit)
            except TypeError:
                return self.semantic_engine.search(question)
        return []

    def _topic_detect(self, text: str) -> list[str]:
        if hasattr(self.semantic_engine, "topic_engine"):
            engine = getattr(self.semantic_engine, "topic_engine")
            if hasattr(engine, "detect"):
                return engine.detect(text)
        return []

    def _cross_refs_for(self, verse_obj) -> list[str]:
        refs: list[str] = []
        ref_key = self._format_ref(verse_obj)

        # Prefer DB-backed refs if available.
        if hasattr(self.db, "get_cross_references"):
            try:
                items = self.db.get_cross_references(
                    verse_obj.translation,
                    verse_obj.book,
                    verse_obj.chapter,
                    verse_obj.verse,
                )
                for item in items:
                    if isinstance(item, str):
                        refs.append(item)
                    else:
                        book = getattr(item, "book", None)
                        chapter = getattr(item, "chapter", None)
                        verse = getattr(item, "verse", None)
                        if book and chapter and verse:
                            refs.append(f"{book.title()} {chapter}:{verse}")
            except Exception:
                pass

        # Fallback to compatibility constant.
        for ref in CROSS_REFERENCES.get(ref_key, []):
            if ref not in refs:
                refs.append(ref)

        return refs

    def _word_study_for(self, verse_obj) -> list[str]:
        hints: list[str] = []
        if hasattr(self.strongs_engine, "extract_word_links"):
            try:
                links = self.strongs_engine.extract_word_links(verse_obj)
                for word, code in links[:8]:
                    if code:
                        hints.append(f"{word} — {code}")
            except Exception:
                pass
        return hints

    def _format_ref(self, verse_obj) -> str:
        return f"{verse_obj.book.title()} {verse_obj.chapter}:{verse_obj.verse}"

    def answer(self, question: str, translation: str | None = None) -> StudyAssistantAnswer:
        question = (question or "").strip()
        translation = (translation or "").strip().lower() or None

        if not question:
            return StudyAssistantAnswer(
                title="AI Bible Study Assistant",
                summary="Enter a question to generate a study guide.",
                semantic_engine_mode=getattr(self.semantic_engine, "mode", "unknown"),
            )

        hits = self._semantic_hits(question, translation, limit=8)
        mode = getattr(self.semantic_engine, "mode", "unknown")

        if not hits:
            tr_text = translation.upper() if translation else "the selected translation"
            return StudyAssistantAnswer(
                title=f"Study Guide: {question}",
                summary=f"No passages were found in {tr_text}. Try a broader query or import more Bible text.",
                semantic_engine_mode=mode,
                reflection_questions=[
                    "What key words could you try instead?",
                    "Would a shorter topical query help?",
                ],
            )

        key_passages: list[str] = []
        cross_references: list[str] = []
        word_study: list[str] = []
        all_topics: list[str] = []

        for hit in hits[:5]:
            verse_obj = getattr(hit, "verse", hit)
            ref = self._format_ref(verse_obj)
            key_passages.append(f"{ref} — {verse_obj.text}")

            for topic in self._topic_detect(verse_obj.text):
                if topic not in all_topics:
                    all_topics.append(topic)

            for ref_text in self._cross_refs_for(verse_obj):
                if ref_text not in cross_references:
                    cross_references.append(ref_text)

            for hint in self._word_study_for(verse_obj):
                if hint not in word_study:
                    word_study.append(hint)

        if not cross_references:
            for hit in hits[5:8]:
                verse_obj = getattr(hit, "verse", hit)
                ref = self._format_ref(verse_obj)
                if ref not in cross_references:
                    cross_references.append(ref)

        summary = (
            f"Question: {question}\n\n"
            f"This study guide was generated from passages found in "
            f"{translation.upper() if translation else 'the current translation'}. "
            f"The most relevant passages emphasize themes such as "
            f"{', '.join(all_topics[:5]) if all_topics else 'faith, context, and application'}."
        )

        reflection_questions = [
            "What does this passage reveal about God's character?",
            "How does the surrounding context change your understanding of the verse?",
            "Which linked references deepen or balance this theme?",
        ]

        return StudyAssistantAnswer(
            title=f"Study Guide: {question}",
            summary=summary,
            detected_topics=all_topics[:10],
            semantic_engine_mode=mode,
            key_passages=key_passages,
            cross_references=cross_references[:12],
            word_study=word_study[:12],
            reflection_questions=reflection_questions,
        )
