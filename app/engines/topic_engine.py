from __future__ import annotations

TOPICS = {
    "faith": ["faith", "believe", "belief", "trust", "hope"],
    "love": ["love", "charity", "kindness", "compassion"],
    "salvation": ["save", "saved", "salvation", "redeem", "redeemed"],
    "grace": ["grace", "mercy", "favor"],
    "sin": ["sin", "sins", "iniquity", "transgression", "wickedness"],
    "forgiveness": ["forgive", "forgiven", "forgiveness", "pardon", "cleanse"],
    "prayer": ["pray", "prayer", "ask", "supplication"],
    "wisdom": ["wisdom", "understanding", "discernment"],
}


class TopicEngine:
    def detect(self, text: str) -> list[str]:
        lowered = text.lower()
        found: list[str] = []
        for topic, words in TOPICS.items():
            if any(word in lowered for word in words):
                found.append(topic)
        return found

    def expand(self, query: str) -> list[str]:
        words = query.lower().split()
        expanded = set(words)
        for word in words:
            for topic, topic_words in TOPICS.items():
                if word == topic or word in topic_words:
                    expanded.add(topic)
                    expanded.update(topic_words)
        return sorted(expanded)
