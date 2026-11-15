"""Multi-query retrieval, deduplication, ranking, and adjacent context."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

from . import config
from .adapters import legacy_evidence_to_contract
from .retriever import retrieve_passages

TOP_K_PER_QUERY = 5
_NAME_ALIASES = {
    "rama": ("rama", "raghava"),
    "vishvamitra": ("vishvamitra", "visvamitra"),
    "maricha": ("maricha", "marica"),
    "subahu": ("subahu", "suvahu", "suvahu"),
    "yajna": ("yajna", "sacrifice", "altar", "sacrifices"),
}


def _plain(text: object) -> str:
    value = unicodedata.normalize("NFD", str(text).casefold())
    return "".join(char for char in value if unicodedata.category(char) != "Mn")


def _scene_relevance(situation: str, passage: dict[str, Any]) -> int:
    query = _plain(situation)
    body = _plain(passage.get("text", ""))
    matched = [
        entity for entity, aliases in _NAME_ALIASES.items()
        if any(alias in query for alias in aliases) and any(alias in body for alias in aliases)
    ]
    passage["matched_scene_entities"] = matched
    passage["scene_relevance_score"] = len(matched)
    return len(matched)


def load_chunk_metadata(metadata_path: str | Path = config.METADATA_PATH) -> list[dict[str, Any]]:
    with Path(metadata_path).open("r", encoding="utf-8") as stream:
        metadata = json.load(stream)
    records = metadata.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Metadata records must be a list.")
    return records


def build_search_queries(situation: str) -> list[str]:
    return [
        situation,
        f"Events and actions involving {situation}",
        f"People, places, and important details in {situation}",
    ]


def normalize_primary_passage(passage: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": passage.get("chunk_id"),
        "kanda": passage.get("kanda"),
        "website_chapter": passage.get("website_chapter"),
        "part": passage.get("part"),
        "section_id": passage.get("section_id"),
        "section_number": passage.get("section_number"),
        "section_name": passage.get("section_name"),
        "source_id": passage.get("source_id"),
        "source": passage.get("source"),
        "source_file": passage.get("source_file"),
        "source_url": passage.get("source_url"),
        "translator": passage.get("translator"),
        "similarity_score": passage.get("similarity_score"),
        "text": passage.get("text", ""),
        "rank": passage.get("rank"),
        "retrieval_role": "primary",
        "matched_queries": [],
    }


def retrieve_multiple_queries(
    situation: str,
    *,
    retrieve_fn: Callable[..., list[dict[str, Any]]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    search = retrieve_fn or retrieve_passages
    passages_by_id: dict[str, dict[str, Any]] = {}
    query_results = []
    for query in build_search_queries(situation):
        results = search(query, top_k=TOP_K_PER_QUERY)
        query_results.append({"query": query, "result_count": len(results)})
        for passage in results:
            chunk_id = passage.get("chunk_id")
            if not chunk_id:
                continue
            if chunk_id not in passages_by_id:
                normalized = normalize_primary_passage(passage)
                normalized["matched_queries"] = [query]
                passages_by_id[chunk_id] = normalized
                continue
            existing = passages_by_id[chunk_id]
            existing["matched_queries"].append(query)
            new_score = passage.get("similarity_score")
            old_score = existing.get("similarity_score")
            if new_score is not None and (old_score is None or new_score > old_score):
                updated = normalize_primary_passage(passage)
                updated["matched_queries"] = existing["matched_queries"]
                passages_by_id[chunk_id] = updated

    ranked = list(passages_by_id.values())
    for passage in ranked:
        _scene_relevance(situation, passage)
    ranked.sort(key=lambda item: (
        item["scene_relevance_score"],
        item["similarity_score"] if item["similarity_score"] is not None else -1,
    ), reverse=True)
    for rank, passage in enumerate(ranked, start=1):
        passage["combined_rank"] = rank
    return ranked, query_results


def expand_with_adjacent_chunks(
    primary_passages: list[dict[str, Any]], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_position = {}
    by_id = {}
    for record in records:
        chunk_id = record.get("chunk_id")
        if chunk_id:
            by_id[chunk_id] = record
        key = (record.get("source_id"), record.get("source_file"), record.get("section_id"), record.get("chunk_index"))
        by_position[key] = record

    expanded = []
    included_ids = set()
    for passage in primary_passages:
        chunk_id = passage.get("chunk_id")
        if not chunk_id or chunk_id in included_ids:
            continue
        primary = dict(passage)
        primary["retrieval_role"] = "primary"
        expanded.append(primary)
        included_ids.add(chunk_id)
        source_record = by_id.get(chunk_id)
        if source_record is None or not isinstance(source_record.get("chunk_index"), int):
            continue
        for neighbor_index in (source_record["chunk_index"] - 1, source_record["chunk_index"] + 1):
            key = (source_record.get("source_id"), source_record.get("source_file"), source_record.get("section_id"), neighbor_index)
            neighbor = by_position.get(key)
            if neighbor is None:
                continue
            neighbor_id = neighbor.get("chunk_id")
            if not neighbor_id or neighbor_id in included_ids:
                continue
            adjacent = dict(neighbor)
            adjacent["retrieval_role"] = "adjacent_context"
            adjacent["similarity_score"] = None
            adjacent["matched_queries"] = []
            expanded.append(adjacent)
            included_ids.add(neighbor_id)
    return expanded


def get_ramayana_evidence(
    situation: str,
    *,
    retrieve_fn: Callable[..., list[dict[str, Any]]] | None = None,
    metadata_loader: Callable[[], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    if not isinstance(situation, str) or not situation.strip():
        raise ValueError("Situation must be a non-empty string.")
    try:
        primary, query_results = retrieve_multiple_queries(situation.strip(), retrieve_fn=retrieve_fn)
        records = (metadata_loader or load_chunk_metadata)()
        expanded = expand_with_adjacent_chunks(primary, records)
        return {
            "status": "success" if primary else "insufficient_evidence",
            "user_situation": situation,
            "source_information": {"source": "Valmiki Ramayana", "translator": "Manmatha Nath Dutt"},
            "retrieval_information": {
                "retrieval_method": "multi-query FAISS semantic search",
                "queries": query_results,
                "top_k_per_query": TOP_K_PER_QUERY,
                "primary_passage_count": len(primary),
                "expanded_passage_count": len(expanded),
                "context_expansion": "previous_and_next_same_section",
                "evidence_relevance": "entity_overlap_ranked",
                "primary_evidence_chunk_ids": [p.get("chunk_id") for p in primary],
            },
            "evidence_passages": expanded,
            "error": None,
        }
    except Exception as error:
        return {
            "status": "retrieval_error", "user_situation": situation,
            "source_information": {}, "retrieval_information": {},
            "evidence_passages": [], "error": str(error),
        }


def format_evidence_for_llm(evidence: dict[str, Any]) -> str:
    return json.dumps(evidence, ensure_ascii=False, indent=2)


def retrieve_rag_evidence(situation: str):
    """Return the Phase 1 contract representation of retrieved evidence."""
    legacy = get_ramayana_evidence(situation)
    return legacy_evidence_to_contract(legacy)

