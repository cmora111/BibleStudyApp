# Embeddings-Based Semantic Search

Ultimate Bible App v6 uses an **embeddings-first semantic engine**.

## Default behavior

The app tries to load this model:

- `sentence-transformers/all-MiniLM-L6-v2`

If available, verses are encoded into transformer embeddings and cached locally. Query search runs by cosine similarity against those vectors.

## Fallback behavior

If `sentence-transformers` is not installed or a model is not available locally, the app automatically falls back to a deterministic hashed-vector semantic mode so the app still works offline.

## Cache files

Embeddings are cached under the app cache directory so repeated launches are faster.

## Rebuild

Use **File → Rebuild Semantic Index** after importing new Bible text.
