"""FAISS index loading and metadata validation."""

import json
from pathlib import Path
from typing import Any

import faiss

from . import config


REQUIRED_RECORD_FIELDS = (
    "chunk_id", "source_id", "source", "translator", "source_url", "kanda",
    "website_chapter", "part", "section_id", "section_number", "section_name",
    "source_file", "chunk_index", "text",
)


def validate_records(records: Any) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError("FAISS metadata records must be a list.")
    seen_ids: set[str] = set()
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"FAISS metadata record {position} must be an object.")
        record_id = record.get("chunk_id")
        suffix = f" ({record_id})" if record_id else f" at position {position}"
        for field in REQUIRED_RECORD_FIELDS:
            value = record.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Missing required provenance field {field}{suffix}.")
        if record["chunk_id"] in seen_ids:
            raise ValueError(f"Duplicate chunk_id {record['chunk_id']!r} in FAISS metadata.")
        seen_ids.add(record["chunk_id"])
        if record["source_id"] != config.SOURCE_ID:
            raise ValueError(f"Unexpected source_id for chunk {record['chunk_id']!r}.")
        if record["source"] != config.WORK:
            raise ValueError(f"Unexpected Ramayana work for chunk {record['chunk_id']!r}.")
        if record["translator"] != config.TRANSLATOR:
            raise ValueError(f"Unexpected translator for chunk {record['chunk_id']!r}.")
        kanda = record["kanda"]
        if kanda not in config.ALLOWED_KANDAS:
            raise ValueError(f"Out-of-scope Kanda {kanda!r} for chunk {record['chunk_id']!r}.")
        expected_folder = "bala_kanda" if kanda == "Bala Kanda" else "aranya_kanda"
        source_file = str(record["source_file"]).replace("\\", "/").casefold()
        if not source_file.startswith(expected_folder + "/"):
            raise ValueError(f"source_file/Kanda mismatch for chunk {record['chunk_id']!r}.")
    return records


def load_vector_store(
    index_path: str | Path = config.INDEX_PATH,
    metadata_path: str | Path = config.METADATA_PATH,
    *,
    model_name: str = config.EMBEDDING_MODEL,
) -> tuple[Any, dict[str, Any]]:
    """Load the existing index and fail closed on invalid records/metadata."""
    index_path = Path(index_path)
    metadata_path = Path(metadata_path)
    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    index = faiss.read_index(str(index_path))
    with metadata_path.open("r", encoding="utf-8") as stream:
        metadata = json.load(stream)
    if not isinstance(metadata, dict):
        raise ValueError("FAISS metadata must be a JSON object.")
    if metadata.get("model_name") != model_name:
        raise ValueError("Embedding model does not match the stored index.")
    if metadata.get("source_id") != config.SOURCE_ID:
        raise ValueError("The vector store does not contain the expected Dutt source.")

    records = validate_records(metadata.get("records"))
    if index.ntotal != len(records):
        raise ValueError("FAISS index and metadata record counts do not match.")
    if index.d != metadata.get("dimension"):
        raise ValueError("FAISS index dimension does not match metadata.")
    if index.ntotal == 0:
        raise ValueError("The FAISS index is empty.")
    if getattr(index, "metric_type", faiss.METRIC_INNER_PRODUCT) != faiss.METRIC_INNER_PRODUCT:
        raise ValueError("FAISS index metric does not match configured inner_product metric.")
    return index, metadata

