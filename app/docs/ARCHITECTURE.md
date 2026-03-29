# Architecture

## Core
- `bible_db.py` — SQLite persistence
- `importers.py` — pipe-delimited Bible text importer
- `utils.py` — formatting helpers

## Engines
- `topic_engine.py` — theme detection and expansion
- `semantic_search.py` — ranked topical retrieval
- `study_assistant.py` — AI study-guide generation
- `commentary.py` — local commentary generation
- `knowledge_graph.py` — HTML graph export

## UI
- `main_window.py` — integrated desktop application

## Design goals
- modular
- offline-first
- easy to extend
- safe to add licensed Bible texts later
