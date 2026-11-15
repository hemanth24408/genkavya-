import json

import pytest

from genkavya.rag.corpus_audit import audit_corpus


def make_record(chunk_id="BALA_KANDA_PART_01_SEC_001_CHUNK_001", *, kanda="Bala Kanda", text="A source-grounded passage."):
    folder = "bala_kanda" if kanda == "Bala Kanda" else "aranya_kanda"
    return {
        "chunk_id": chunk_id,
        "source_id": "VALMIKI_RAMAYANA_DUTT",
        "source": "The Ramayana of Valmiki",
        "translator": "Manmatha Nath Dutt",
        "source_url": "https://example.org/source",
        "kanda": kanda,
        "website_chapter": "2",
        "part": 1,
        "section_id": "2.1",
        "section_number": 1,
        "section_name": "I",
        "source_file": f"{folder}/{folder}_part_01.txt",
        "chunk_index": 1,
        "text": text,
    }


def write_inputs(tmp_path, processed_records, indexed_records=None, *, metadata_overrides=None):
    processed_dir = tmp_path / "processed"
    (processed_dir / "bala_kanda").mkdir(parents=True)
    (processed_dir / "bala_kanda" / "part_chunks.json").write_text(
        json.dumps(processed_records), encoding="utf-8"
    )
    metadata_path = tmp_path / "metadata.json"
    metadata = {"total_vectors": len(indexed_records if indexed_records is not None else processed_records),
                "records": indexed_records if indexed_records is not None else processed_records}
    metadata.update(metadata_overrides or {})
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return processed_dir, metadata_path


def audit(tmp_path, processed_records, indexed_records=None):
    processed_dir, metadata_path = write_inputs(tmp_path, processed_records, indexed_records)
    return audit_corpus(
        processed_dir, metadata_path,
        expected_counts_by_kanda={"Bala Kanda": len(processed_records), "Aranya Kanda": 0},
    )


def test_matching_in_scope_records_pass_without_modifying_inputs(tmp_path):
    records = [make_record()]
    processed_dir, metadata_path = write_inputs(tmp_path, records)
    original_processed = (processed_dir / "bala_kanda" / "part_chunks.json").read_bytes()
    original_metadata = metadata_path.read_bytes()

    result = audit_corpus(
        processed_dir, metadata_path,
        expected_counts_by_kanda={"Bala Kanda": 1, "Aranya Kanda": 0},
    )

    assert result.passed is True
    assert result.processed_record_count == result.indexed_record_count == 1
    assert result.errors == []
    assert result.accounting_limitation
    assert (processed_dir / "bala_kanda" / "part_chunks.json").read_bytes() == original_processed
    assert metadata_path.read_bytes() == original_metadata


def test_out_of_scope_kanda_and_source_path_mismatch_are_errors(tmp_path):
    record = make_record(kanda="Yuddha Kanda")
    result = audit(tmp_path, [record])
    codes = {issue.code for issue in result.errors}
    assert "out_of_scope_kanda" in codes
    assert "unexpected_kanda_count" in codes
    assert result.passed is False


@pytest.mark.parametrize("field,value,code", [
    ("source_id", "OTHER", "unexpected_source_id"),
    ("source", "Another Work", "unexpected_work"),
    ("translator", "Unknown Translator", "unexpected_translator"),
    ("source_url", "", "missing_required_field"),
    ("text", "  ", "missing_required_field"),
    ("chunk_id", "", "missing_required_field"),
])
def test_identity_and_required_field_issues_include_record_id(tmp_path, field, value, code):
    record = make_record()
    record[field] = value
    result = audit(tmp_path, [record])
    issue = next(issue for issue in result.errors if issue.code == code)
    assert issue.record_id in (None, record.get("chunk_id"))
    assert issue.message


def test_duplicate_ids_are_reported(tmp_path):
    record = make_record()
    result = audit(tmp_path, [record, dict(record)])
    assert any(issue.code == "duplicate_chunk_id" and issue.record_id == record["chunk_id"]
               for issue in result.errors)


def test_processed_and_index_records_must_match_by_id_and_text(tmp_path):
    processed = make_record()
    text_mismatch = dict(processed, text="Different passage")
    unexpected = make_record("BALA_KANDA_PART_01_SEC_001_CHUNK_002")
    result = audit(tmp_path, [processed], [text_mismatch, unexpected])
    codes = {issue.code for issue in result.errors}
    assert "chunk_text_mismatch" in codes
    assert "unexpected_index_record" in codes
    assert result.passed is False


def test_source_file_kanda_mismatch_and_declared_count_mismatch_are_reported(tmp_path):
    record = make_record()
    record["source_file"] = "aranya_kanda/aranya_kanda_part_01.txt"
    processed_dir, metadata_path = write_inputs(tmp_path, [record], metadata_overrides={"total_vectors": 99})
    result = audit_corpus(
        processed_dir, metadata_path,
        expected_counts_by_kanda={"Bala Kanda": 1, "Aranya Kanda": 0},
    )
    codes = {issue.code for issue in result.errors}
    assert "source_file_kanda_mismatch" in codes
    assert "declared_vector_count_mismatch" in codes


def test_invalid_json_is_a_structured_error(tmp_path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    (processed_dir / "broken_chunks.json").write_text("{", encoding="utf-8")
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps({"records": []}), encoding="utf-8")
    result = audit_corpus(processed_dir, metadata_path, expected_counts_by_kanda={"Bala Kanda": 0, "Aranya Kanda": 0})
    assert result.passed is False
    assert any(issue.code == "processed_json_unreadable" for issue in result.errors)

