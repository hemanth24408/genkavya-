"""Focused tests for the modular RAG components and production adapters."""

import json

import numpy as np
import pytest

from genkavya.rag import config, evidence, index_loader, retriever
from genkavya.rag.adapters import legacy_evidence_to_contract, passage_to_contract


def record(chunk_id="c1", **changes):
    value = {
        "chunk_id": chunk_id,
        "source_id": config.SOURCE_ID,
        "source": config.WORK,
        "translator": config.TRANSLATOR,
        "source_url": "https://example.org/ramayana/section",
        "kanda": "Bala Kanda",
        "website_chapter": "2",
        "part": 1,
        "section_id": "2.1",
        "section_number": 1,
        "section_name": "I",
        "source_file": "bala_kanda/bala_kanda_part_01.txt",
        "chunk_index": 1,
        "text": "Rama visits the sage.",
    }
    value.update(changes)
    return value


class Index:
    ntotal = 1
    d = 2
    metric_type = 0

    def search(self, query, top_k):
        self.query = query
        self.top_k = top_k
        return np.array([[0.7]], dtype=np.float32), np.array([[0]], dtype=np.int64)


class Model:
    def encode(self, texts, **kwargs):
        self.texts = texts
        self.kwargs = kwargs
        return np.array([[1.0, 0.0]], dtype=np.float32)


def test_per_record_loader_validation_checks_scope_identity_and_provenance():
    assert index_loader.validate_records([record()])[0]["chunk_id"] == "c1"
    for invalid in (
        record(kanda="Yuddha Kanda"),
        record(translator="Unknown"),
        record(source_id="OTHER"),
        record(source_url=""),
        record(source_file="aranya_kanda/part.txt"),
    ):
        with pytest.raises(ValueError):
            index_loader.validate_records([invalid])


def test_index_loader_uses_faiss_reader_and_checks_consistency(monkeypatch, tmp_path):
    index_path = tmp_path / "index.bin"
    index_path.write_bytes(b"mock")
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps({
        "model_name": config.EMBEDDING_MODEL,
        "source_id": config.SOURCE_ID,
        "dimension": 2,
        "records": [record()],
    }), encoding="utf-8")
    index = Index()
    monkeypatch.setattr(index_loader.faiss, "read_index", lambda _path: index)

    loaded_index, metadata = index_loader.load_vector_store(index_path, metadata_path)

    assert loaded_index is index
    assert metadata["records"][0]["chunk_id"] == "c1"


def test_modular_retriever_normalizes_query_and_preserves_provenance():
    index = Index()
    model = Model()
    results = retriever.retrieve_passages(
        "  scene ",
        top_k=5,
        store_loader=lambda: (index, {"records": [record()]}),
        model_loader=lambda: model,
    )
    assert model.texts == ["scene"]
    assert model.kwargs["normalize_embeddings"] is True
    assert index.top_k == 1
    assert results[0]["translator"] == config.TRANSLATOR
    assert results[0]["source_url"] == record()["source_url"]


def test_evidence_pipeline_keeps_adjacent_context_distinct(monkeypatch):
    primary = record(chunk_index=2)
    previous = record("prev", chunk_index=1, text="Previous passage.")
    following = record("next", chunk_index=3, text="Following passage.")
    search = lambda _query, top_k: [dict(primary, similarity_score=0.7, rank=1)]
    passages, _ = evidence.retrieve_multiple_queries("Rama visits the sage", retrieve_fn=search)
    expanded = evidence.expand_with_adjacent_chunks(passages, [previous, primary, following])
    assert [p["retrieval_role"] for p in expanded] == ["primary", "adjacent_context", "adjacent_context"]
    assert expanded[1]["similarity_score"] is None
    assert expanded[1]["source_url"] == previous["source_url"]


def test_production_adapter_preserves_provenance_and_metric_metadata():
    mapped = passage_to_contract(dict(record(), similarity_score=0.7), rank=1)
    assert mapped.provenance.source_id == config.SOURCE_ID
    assert mapped.provenance.kanda == "Bāla Kāṇḍa"
    assert mapped.provenance.website_chapter == "2"
    assert mapped.score_metadata.metric == "inner_product"
    assert mapped.score_metadata.embedding_normalized is True


def test_evidence_adapter_returns_contract_and_distinguishes_adjacent_role():
    primary = record()
    adjacent = record("c2", chunk_index=2)
    adjacent["retrieval_role"] = "adjacent_context"
    adjacent["similarity_score"] = None
    evidence_contract = legacy_evidence_to_contract({
        "status": "success",
        "user_situation": "Rama visits a sage.",
        "evidence_passages": [dict(primary, similarity_score=0.8), adjacent],
    })
    assert evidence_contract.passages[0].retrieval_role == "primary"
    assert evidence_contract.passages[1].retrieval_role == "adjacent_context"
    assert evidence_contract.passages[1].score is None
    assert evidence_contract.passages[1].provenance.source_file == adjacent["source_file"]

