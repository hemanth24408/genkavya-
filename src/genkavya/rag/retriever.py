"""Normalized query embedding and FAISS passage retrieval."""

from typing import Any, Callable

import numpy as np
from sentence_transformers import SentenceTransformer

from . import config
from .index_loader import load_vector_store

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("Loading embedding model...")
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def retrieve_passages(
    query: str,
    top_k: int = 2,
    min_similarity: float | None = None,
    *,
    store_loader: Callable[[], tuple[Any, dict[str, Any]]] | None = None,
    model_loader: Callable[[], Any] | None = None,
) -> list[dict[str, Any]]:
    """Return legacy-shaped passage dictionaries from normalized FAISS search.

    The optional loaders are injection seams used by the legacy facade and tests.
    No similarity threshold is applied unless the caller explicitly supplies one.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string.")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    if min_similarity is not None:
        if not isinstance(min_similarity, (int, float)):
            raise ValueError("min_similarity must be a number or None.")
        if not -1 <= min_similarity <= 1:
            raise ValueError("min_similarity must be between -1 and 1.")

    index, metadata = (store_loader or load_vector_store)()
    records = metadata["records"]
    search_k = min(top_k, index.ntotal)
    embedding = (model_loader or get_model)().encode(
        [query.strip()], convert_to_numpy=True, normalize_embeddings=True
    ).astype("float32")
    if embedding.ndim != 2 or embedding.shape[1] != index.d:
        raise ValueError("Query embedding dimension does not match FAISS index.")

    scores, indices = index.search(embedding, search_k)
    results: list[dict[str, Any]] = []
    for score, idx in zip(scores[0], indices[0]):
        # Ignore all invalid/sentinel indices; never let -2 index from the end.
        if idx < 0 or idx >= len(records):
            continue
        score = float(score)
        if min_similarity is not None and score < min_similarity:
            continue
        passage = records[int(idx)]
        results.append({
            "chunk_id": passage.get("chunk_id"),
            "kanda": passage.get("kanda"),
            "website_chapter": passage.get("website_chapter"),
            "part": passage.get("part"),
            "section_id": passage.get("section_id"),
            "section_number": passage.get("section_number"),
            "section_name": passage.get("section_name"),
            "source_id": passage.get("source_id"),
            "source": passage.get("source"),
            "translator": passage.get("translator"),
            "source_file": passage.get("source_file"),
            "source_url": passage.get("source_url"),
            "similarity_score": score,
            "text": passage.get("text", ""),
        })
    return results

