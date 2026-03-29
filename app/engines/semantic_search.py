from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.bible_db import BibleDB, VerseRecord
from app.core.config import DEFAULT_EMBEDDING_MODEL, EMBEDDINGS_CACHE_FILE, EMBEDDINGS_META_FILE
from app.engines.topic_engine import TopicEngine

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional runtime dependency
    SentenceTransformer = None


@dataclass(slots=True)
class SearchHit:
    score: float
    verse: VerseRecord
    matched_terms: list[str]
    engine_mode: str


class SemanticSearchEngine:
    """Embeddings-first semantic search with hashed-vector fallback.

    If sentence-transformers is available, this engine uses a real transformer
    embedding model and caches verse embeddings to disk. Otherwise it falls back
    to a deterministic hashed embedding so the app still runs offline.
    """

    def __init__(self, db: BibleDB, translation: str = "kjv", model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.db = db
        self.translation = translation
        self.model_name = model_name
        self.topic_engine = TopicEngine()
        self._model = None
        self._mode = "hash-fallback"
        self._verses: list[VerseRecord] = []
        self._texts: list[str] = []
        self._embeddings: np.ndarray = np.zeros((0, 256), dtype=np.float32)
        self.rebuild()

    @property
    def mode(self) -> str:
        return self._mode

    def set_translation(self, translation: str) -> None:
        if translation != self.translation:
            self.translation = translation
            self.rebuild()

    def _translation_signature(self, verses: list[VerseRecord]) -> str:
        basis = "\n".join(f"{v.translation}|{v.book}|{v.chapter}|{v.verse}|{v.text}" for v in verses)
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()

    def _get_model(self):
        if SentenceTransformer is None:
            self._mode = "hash-fallback"
            return None
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        self._mode = f"transformer:{self.model_name}"
        return self._model

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _hashed_embed(self, texts: list[str], dims: int = 256) -> np.ndarray:
        matrix = np.zeros((len(texts), dims), dtype=np.float32)
        for i, text in enumerate(texts):
            for token in self.topic_engine.expand(text):
                idx = int(hashlib.md5(token.lower().encode("utf-8")).hexdigest(), 16) % dims
                matrix[i, idx] += 1.0
        return self._normalize(matrix)

    def _cache_exists(self, signature: str) -> bool:
        return EMBEDDINGS_CACHE_FILE.exists() and EMBEDDINGS_META_FILE.exists() and self._read_meta().get("signature") == signature

    def _read_meta(self) -> dict:
        if not EMBEDDINGS_META_FILE.exists():
            return {}
        return json.loads(EMBEDDINGS_META_FILE.read_text(encoding="utf-8"))

    def _write_cache(self, signature: str, embeddings: np.ndarray) -> None:
        np.savez_compressed(EMBEDDINGS_CACHE_FILE, embeddings=embeddings)
        EMBEDDINGS_META_FILE.write_text(
            json.dumps(
                {
                    "signature": signature,
                    "translation": self.translation,
                    "model_name": self.model_name,
                    "mode": self._mode,
                    "count": len(self._texts),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_cache(self) -> np.ndarray:
        payload = np.load(EMBEDDINGS_CACHE_FILE)
        return payload["embeddings"]

    def rebuild(self) -> None:
        verses = self.db.all_verses(self.translation)
        self._verses = verses
        self._texts = [v.text for v in verses]
        if not verses:
            self._embeddings = np.zeros((0, 256), dtype=np.float32)
            self._mode = "empty"
            return

        signature = self._translation_signature(verses)
        try:
            model = self._get_model()
            if model is not None:
                if self._cache_exists(signature):
                    self._embeddings = self._load_cache()
                    meta = self._read_meta()
                    self._mode = meta.get("mode", self._mode)
                else:
                    raw = model.encode(self._texts, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
                    self._embeddings = raw.astype(np.float32)
                    self._write_cache(signature, self._embeddings)
                return
        except Exception:
            self._mode = "hash-fallback"

        self._embeddings = self._hashed_embed(self._texts)
        self._write_cache(signature, self._embeddings)

    def _encode_query(self, query: str) -> np.ndarray:
        expanded = " ".join(self.topic_engine.expand(query))
        model = None
        try:
            model = self._get_model()
        except Exception:
            model = None
        if model is not None and self._mode.startswith("transformer"):
            vec = model.encode([expanded], convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
            return vec.astype(np.float32)[0]
        return self._hashed_embed([expanded])[0]

    def search(self, query: str, limit: int = 25) -> list[SearchHit]:
        query = query.strip()
        if not query or len(self._verses) == 0:
            return []
        qvec = self._encode_query(query)
        scores = self._embeddings @ qvec
        top_indices = np.argsort(scores)[::-1][:limit]
        expanded_terms = {term.lower() for term in self.topic_engine.expand(query)}
        hits: list[SearchHit] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            verse = self._verses[int(idx)]
            matched = sorted({t for t in expanded_terms if t in verse.text.lower()})
            hits.append(SearchHit(score=score, verse=verse, matched_terms=matched, engine_mode=self._mode))
        return hits
