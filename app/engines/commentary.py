from __future__ import annotations

from app.core.bible_db import VerseRecord
from app.engines.topic_engine import TopicEngine


class CommentaryEngine:
    def __init__(self):
        self.topic_engine = TopicEngine()

    def explain(self, verse: VerseRecord) -> str:
        topics = self.topic_engine.detect(verse.text)
        topic_text = ", ".join(topics) if topics else "general discipleship"
        return (
            f"Study note for {verse.book.title()} {verse.chapter}:{verse.verse}\n\n"
            f"Themes: {topic_text}\n"
            f"Observation: This verse emphasizes '{verse.text[:140]}'\n"
            "Interpretation: Compare this verse with nearby context, cross references, and repeated covenant or gospel language.\n"
            "Application: Write one practical response and one prayer based on this passage."
        )
