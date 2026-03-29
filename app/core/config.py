from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path.home() / "UltimateBibleApp"
DATA_DIR = ROOT_DIR / "data"
EXPORT_DIR = ROOT_DIR / "exports"
CACHE_DIR = ROOT_DIR / "cache"
DB_FILE = DATA_DIR / "bible.db"
GRAPH_HTML = EXPORT_DIR / "knowledge_graph.html"
EMBEDDINGS_CACHE_FILE = CACHE_DIR / "semantic_embeddings.npz"
EMBEDDINGS_META_FILE = CACHE_DIR / "semantic_embeddings_meta.json"

DEFAULT_TRANSLATIONS = ["kjv", "web", "asv"]
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

for path in (ROOT_DIR, DATA_DIR, EXPORT_DIR, CACHE_DIR):
    path.mkdir(parents=True, exist_ok=True)
