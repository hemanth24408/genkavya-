"""Read-only integrity audit for processed Ramayana chunks and FAISS metadata.

This module inspects JSON artifacts only. It never changes corpus files or
loads/rebuilds the binary FAISS index.

Accounting limitation: matching processed chunks to FAISS metadata and checking
expected counts cannot prove that a particular source passage was not omitted
if another record was substituted while preserving those counts. A versioned
expected chunk-ID manifest or a separate source-to-chunk verification process
is required to establish that stronger guarantee. This utility does not
regenerate chunks from source documents.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from pydantic import Field

from genkavya.contracts.common import ContractModel


EXPECTED_SOURCE_ID = "VALMIKI_RAMAYANA_DUTT"
EXPECTED_WORK = "The Ramayana of Valmiki"
EXPECTED_TRANSLATOR = "Manmatha Nath Dutt"
EXPECTED_COUNTS_BY_KANDA = {
    "Bala Kanda": 243,
    "Aranya Kanda": 251,
}
EXPECTED_KANDA_DIRECTORIES = {
    "Bala Kanda": "bala_kanda",
    "Aranya Kanda": "aranya_kanda",
}
REQUIRED_FIELDS = (
    "chunk_id",
    "source_id",
    "source",
    "translator",
    "source_url",
    "kanda",
    "website_chapter",
    "part",
    "section_id",
    "section_number",
    "section_name",
    "source_file",
    "chunk_index",
    "text",
)
ACCOUNTING_LIMITATION = (
    "Cross-dataset ID/text agreement and expected record counts cannot prove "
    "that no source passage was omitted if another record was substituted "
    "while preserving the expected counts. A versioned expected chunk-ID "
    "manifest or independent source-to-chunk verification is required."
)


class CorpusAuditIssue(ContractModel):
    severity: Literal["error", "warning"]
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    record_id: str | None = None
    source_path: str | None = None


class CorpusAuditResult(ContractModel):
    passed: bool
    processed_record_count: int = Field(ge=0)
    indexed_record_count: int = Field(ge=0)
    processed_counts_by_kanda: dict[str, int]
    indexed_counts_by_kanda: dict[str, int]
    errors: list[CorpusAuditIssue] = Field(default_factory=list)
    warnings: list[CorpusAuditIssue] = Field(default_factory=list)
    checked_paths: list[str] = Field(default_factory=list)
    accounting_limitation: str = ACCOUNTING_LIMITATION


def _nonempty(value: object) -> bool:
    if value is None:
        return False
    return bool(value.strip()) if isinstance(value, str) else True


def _normalized_relative_path(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/").casefold()


def _check_record(
    record: object,
    *,
    dataset: str,
    source_path: str,
    errors: list[CorpusAuditIssue],
) -> None:
    if not isinstance(record, dict):
        errors.append(CorpusAuditIssue(
            severity="error", code="record_not_object",
            message=f"{dataset} record must be a JSON object.", source_path=source_path,
        ))
        return

    record_id = record.get("chunk_id") if isinstance(record.get("chunk_id"), str) else None
    for field in REQUIRED_FIELDS:
        if not _nonempty(record.get(field)):
            errors.append(CorpusAuditIssue(
                severity="error", code="missing_required_field",
                message=f"{dataset} record has a missing or empty required field: {field}.",
                record_id=record_id, source_path=source_path,
            ))

    if record.get("source_id") != EXPECTED_SOURCE_ID:
        errors.append(CorpusAuditIssue(
            severity="error", code="unexpected_source_id",
            message=f"Expected source_id {EXPECTED_SOURCE_ID!r}; found {record.get('source_id')!r}.",
            record_id=record_id, source_path=source_path,
        ))
    if record.get("source") != EXPECTED_WORK:
        errors.append(CorpusAuditIssue(
            severity="error", code="unexpected_work",
            message=f"Expected work {EXPECTED_WORK!r}; found {record.get('source')!r}.",
            record_id=record_id, source_path=source_path,
        ))
    if record.get("translator") != EXPECTED_TRANSLATOR:
        errors.append(CorpusAuditIssue(
            severity="error", code="unexpected_translator",
            message=f"Expected translator {EXPECTED_TRANSLATOR!r}; found {record.get('translator')!r}.",
            record_id=record_id, source_path=source_path,
        ))

    kanda = record.get("kanda")
    if kanda not in EXPECTED_KANDA_DIRECTORIES:
        errors.append(CorpusAuditIssue(
            severity="error", code="out_of_scope_kanda",
            message=f"Kanda {kanda!r} is outside the allowed corpus scope.",
            record_id=record_id, source_path=source_path,
        ))
    else:
        expected_dir = EXPECTED_KANDA_DIRECTORIES[kanda]
        source_file = _normalized_relative_path(record.get("source_file"))
        if not source_file.startswith(expected_dir + "/"):
            errors.append(CorpusAuditIssue(
                severity="error", code="source_file_kanda_mismatch",
                message=(f"Kanda {kanda!r} requires source_file under "
                         f"{expected_dir!r}; found {record.get('source_file')!r}."),
                record_id=record_id, source_path=source_path,
            ))


def _load_processed_records(
    chunks_dir: Path,
    errors: list[CorpusAuditIssue],
    checked_paths: list[str],
) -> list[tuple[object, str]]:
    if not chunks_dir.exists() or not chunks_dir.is_dir():
        errors.append(CorpusAuditIssue(
            severity="error", code="processed_directory_missing",
            message=f"Processed chunks directory does not exist: {chunks_dir}.",
            source_path=str(chunks_dir),
        ))
        return []

    files = sorted(chunks_dir.rglob("*_chunks.json"))
    if not files:
        errors.append(CorpusAuditIssue(
            severity="error", code="processed_files_missing",
            message=f"No *_chunks.json files found under {chunks_dir}.",
            source_path=str(chunks_dir),
        ))
        return []

    records: list[tuple[object, str]] = []
    for path in files:
        checked_paths.append(str(path))
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(CorpusAuditIssue(
                severity="error", code="processed_json_unreadable",
                message=f"Could not read processed chunk JSON: {exc}.", source_path=str(path),
            ))
            continue
        if not isinstance(content, list):
            errors.append(CorpusAuditIssue(
                severity="error", code="processed_file_not_list",
                message="Processed chunk JSON must contain a list of records.",
                source_path=str(path),
            ))
            continue
        records.extend((record, str(path)) for record in content)
    return records


def _load_index_records(
    metadata_path: Path,
    errors: list[CorpusAuditIssue],
    checked_paths: list[str],
) -> tuple[list[tuple[object, str]], dict[str, object]]:
    checked_paths.append(str(metadata_path))
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(CorpusAuditIssue(
            severity="error", code="index_metadata_unreadable",
            message=f"Could not read FAISS metadata JSON: {exc}.", source_path=str(metadata_path),
        ))
        return [], {}
    if not isinstance(metadata, dict):
        errors.append(CorpusAuditIssue(
            severity="error", code="index_metadata_not_object",
            message="FAISS metadata JSON must contain an object.", source_path=str(metadata_path),
        ))
        return [], {}

    records = metadata.get("records")
    if not isinstance(records, list):
        errors.append(CorpusAuditIssue(
            severity="error", code="index_records_not_list",
            message="FAISS metadata 'records' field must be a list.", source_path=str(metadata_path),
        ))
        return [], metadata
    return [(record, str(metadata_path)) for record in records], metadata


def _index_records_by_id(
    records: list[tuple[object, str]],
    *,
    dataset: str,
    errors: list[CorpusAuditIssue],
) -> dict[str, tuple[dict[str, object], str]]:
    found: dict[str, tuple[dict[str, object], str]] = {}
    occurrences: defaultdict[str, int] = defaultdict(int)
    for record, source_path in records:
        if not isinstance(record, dict):
            continue
        chunk_id = record.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            continue
        occurrences[chunk_id] += 1
        if chunk_id in found:
            errors.append(CorpusAuditIssue(
                severity="error", code="duplicate_chunk_id",
                message=f"Duplicate chunk ID in {dataset} records (occurrence {occurrences[chunk_id]}).",
                record_id=chunk_id, source_path=source_path,
            ))
        else:
            found[chunk_id] = (record, source_path)
    return found


def audit_corpus(
    processed_chunks_dir: str | Path,
    faiss_metadata_path: str | Path,
    *,
    expected_counts_by_kanda: dict[str, int] | None = None,
) -> CorpusAuditResult:
    """Audit processed chunk JSON against FAISS metadata without writing files.

    Args:
        processed_chunks_dir: Root containing the per-kāṇḍa chunk JSON files.
        faiss_metadata_path: Existing FAISS metadata JSON path (not the index binary).
        expected_counts_by_kanda: Expected record counts. Defaults to the known
            project corpus counts: 243 Bala and 251 Aranya records.

    Returns:
        Structured errors and warnings. A failed audit does not raise for data
        integrity problems; it returns ``passed=False`` with useful diagnostics.
    """
    expected_counts = dict(expected_counts_by_kanda or EXPECTED_COUNTS_BY_KANDA)
    errors: list[CorpusAuditIssue] = []
    warnings: list[CorpusAuditIssue] = []
    checked_paths: list[str] = []

    processed = _load_processed_records(Path(processed_chunks_dir), errors, checked_paths)
    indexed, index_metadata = _load_index_records(Path(faiss_metadata_path), errors, checked_paths)

    for record, source_path in processed:
        _check_record(record, dataset="Processed", source_path=source_path, errors=errors)
    for record, source_path in indexed:
        _check_record(record, dataset="FAISS metadata", source_path=source_path, errors=errors)

    processed_by_id = _index_records_by_id(processed, dataset="processed", errors=errors)
    indexed_by_id = _index_records_by_id(indexed, dataset="FAISS metadata", errors=errors)

    for chunk_id in sorted(processed_by_id.keys() - indexed_by_id.keys()):
        _, source_path = processed_by_id[chunk_id]
        errors.append(CorpusAuditIssue(
            severity="error", code="missing_from_index_metadata",
            message="Processed chunk ID is absent from FAISS metadata records.",
            record_id=chunk_id, source_path=source_path,
        ))
    for chunk_id in sorted(indexed_by_id.keys() - processed_by_id.keys()):
        _, source_path = indexed_by_id[chunk_id]
        errors.append(CorpusAuditIssue(
            severity="error", code="unexpected_index_record",
            message="FAISS metadata contains a chunk ID absent from processed chunks.",
            record_id=chunk_id, source_path=source_path,
        ))
    for chunk_id in sorted(processed_by_id.keys() & indexed_by_id.keys()):
        processed_record, _ = processed_by_id[chunk_id]
        indexed_record, source_path = indexed_by_id[chunk_id]
        if processed_record.get("text") != indexed_record.get("text"):
            errors.append(CorpusAuditIssue(
                severity="error", code="chunk_text_mismatch",
                message="Passage text differs between processed chunks and FAISS metadata.",
                record_id=chunk_id, source_path=source_path,
            ))

    processed_counts = Counter(
        record.get("kanda") for record, _ in processed if isinstance(record, dict)
    )
    indexed_counts = Counter(
        record.get("kanda") for record, _ in indexed if isinstance(record, dict)
    )
    for dataset, counts, records in (
        ("processed", processed_counts, processed),
        ("FAISS metadata", indexed_counts, indexed),
    ):
        for kanda, expected_count in expected_counts.items():
            actual_count = counts.get(kanda, 0)
            if actual_count != expected_count:
                errors.append(CorpusAuditIssue(
                    severity="error", code="expected_kanda_count_mismatch",
                    message=f"{dataset} has {actual_count} {kanda} records; expected {expected_count}.",
                ))
        unexpected = {str(k): v for k, v in counts.items() if k not in expected_counts}
        for kanda, count in sorted(unexpected.items()):
            errors.append(CorpusAuditIssue(
                severity="error", code="unexpected_kanda_count",
                message=f"{dataset} contains {count} record(s) labeled {kanda!r}, outside expected scope.",
            ))

    total_expected = sum(expected_counts.values())
    for key in ("total_vectors",):
        declared = index_metadata.get(key)
        if declared is not None and declared != len(indexed):
            errors.append(CorpusAuditIssue(
                severity="error", code="declared_vector_count_mismatch",
                message=f"FAISS metadata declares {declared} vectors but contains {len(indexed)} records.",
                source_path=str(faiss_metadata_path),
            ))
    if total_expected and not expected_counts:
        warnings.append(CorpusAuditIssue(
            severity="warning", code="expected_inventory_unavailable",
            message="No expected per-kāṇḍa counts or chunk-ID manifest were supplied.",
        ))

    return CorpusAuditResult(
        passed=not errors,
        processed_record_count=len(processed),
        indexed_record_count=len(indexed),
        processed_counts_by_kanda=dict(processed_counts),
        indexed_counts_by_kanda=dict(indexed_counts),
        errors=errors,
        warnings=warnings,
        checked_paths=checked_paths,
    )

