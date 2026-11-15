"""Focused modular retrieval integrity tests with mocked FAISS/model boundaries."""

import json

import numpy as np
import pytest

from genkavya.rag import config, evidence, index_loader, retriever
from genkavya.rag.adapters import passage_to_contract


def make_record(chunk_id="BALA_KANDA_PART_01_SEC_001_CHUNK_001", **overrides):
    record = {
        "chunk_id": chunk_id,
        "source_id": config.SOURCE_ID,
        "source": config.WORK,
        "translator": config.TRANSLATOR,
        "source_url": "https://example.org/ramayana/section-1",
        "kanda": "Bala Kanda",
        "website_chapter": "2",
        "part": 1,
        "section_id": "2.1",
        "section_number": 1,
        "section_name": "I",
        "source_file": "bala_kanda/bala_kanda_part_01.txt",
        "chunk_index": 1,
        "text": "Rama meets the sage in the forest.",
    }
    record.update(overrides)
    return record


class FakeIndex:
    def __init__(self, ntotal=1, dimension=3, indices=None, scores=None):
        self.ntotal = ntotal
        self.d = dimension
        self.metric_type = 0
        self.indices = np.asarray(indices if indices is not None else [[0]], dtype=np.int64)
        self.scores = np.asarray(scores if scores is not None else [[0.75]], dtype=np.float32)
        self.last_top_k = None
        self.last_query = None

    def search(self, query, top_k):
        self.last_query = query
        self.last_top_k = top_k
        return self.scores[:, :top_k], self.indices[:, :top_k]


class FakeModel:
    def __init__(self, dimension=3):
        self.dimension = dimension
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return np.ones((len(texts), self.dimension), dtype=np.float32)


def install_store(monkeypatch, tmp_path, metadata, index):
    index_path = tmp_path / "fake.index"
    index_path.write_bytes(b"mock index placeholder")
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(index_loader.faiss, "read_index", lambda _path: index)
    return index_path, metadata_path


def make_metadata(records, *, dimension=3):
    return {
        "source_id": config.SOURCE_ID,
        "model_name": config.EMBEDDING_MODEL,
        "dimension": dimension,
        "total_vectors": len(records),
        "records": records,
    }


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (make_record(source_id="OTHER"), "Unexpected source_id"),
        (make_record(source="Other Ramayana"), "Unexpected Ramayana work"),
        (make_record(translator="Different Translator"), "Unexpected translator"),
        (make_record(kanda="Yuddha Kanda"), "Out-of-scope Kanda"),
        (make_record(source_file="aranya_kanda/part.txt"), "source_file/Kanda mismatch"),
        (make_record(source_url=""), "Missing required provenance field"),
    ],
)
def test_record_validation_rejects_invalid_source_scope_and_provenance(record, message):
    with pytest.raises(ValueError, match=message):
        index_loader.validate_records([record])


def test_loader_rejects_inconsistent_counts_and_dimensions(monkeypatch, tmp_path):
    record = make_record()
    metadata = make_metadata([record])
    index_path, metadata_path = install_store(monkeypatch, tmp_path, metadata, FakeIndex(ntotal=2))
    with pytest.raises(ValueError, match="record counts"):
        index_loader.load_vector_store(index_path, metadata_path)

    index_path, metadata_path = install_store(monkeypatch, tmp_path, make_metadata([record], dimension=9), FakeIndex())
    with pytest.raises(ValueError, match="dimension does not match"):
        index_loader.load_vector_store(index_path, metadata_path)


def test_loader_rejects_duplicate_chunk_ids_and_empty_index(monkeypatch, tmp_path):
    duplicate = make_record()
    with pytest.raises(ValueError, match="Duplicate chunk_id"):
        index_loader.validate_records([duplicate, dict(duplicate)])

    index_path, metadata_path = install_store(monkeypatch, tmp_path, make_metadata([]), FakeIndex(ntotal=0))
    with pytest.raises(ValueError, match="empty"):
        index_loader.load_vector_store(index_path, metadata_path)


def test_query_validation_rejects_invalid_query_and_search_options():
    store = lambda: (FakeIndex(), {"records": [make_record()]})
    for query in ("", "   ", None):
        with pytest.raises(ValueError, match="non-empty"):
            retriever.retrieve_passages(query, store_loader=store, model_loader=FakeModel)
    for top_k in (0, -1, True):
        with pytest.raises(ValueError, match="top_k"):
            retriever.retrieve_passages("scene", top_k=top_k, store_loader=store, model_loader=FakeModel)


def test_query_is_trimmed_normalized_and_top_k_is_capped():
    index = FakeIndex(ntotal=1)
    model = FakeModel()
    results = retriever.retrieve_passages(
        "  Rama in the forest  ", top_k=9,
        store_loader=lambda: (index, {"records": [make_record()]}), model_loader=lambda: model,
    )
    assert len(results) == 1
    assert index.last_top_k == 1
    assert model.calls[0][0] == ["Rama in the forest"]
    assert model.calls[0][1]["normalize_embeddings"] is True
    assert index.last_query.dtype == np.float32


def test_search_preserves_score_order_and_skips_invalid_faiss_indices():
    records = [make_record("chunk-0"), make_record("chunk-1")]
    index = FakeIndex(ntotal=3, indices=[[1, -1, 0]], scores=[[0.9, 0.8, 0.7]])
    results = retriever.retrieve_passages(
        "scene", top_k=3, store_loader=lambda: (index, {"records": records}), model_loader=FakeModel,
    )
    assert [item["chunk_id"] for item in results] == ["chunk-1", "chunk-0"]
    assert [item["similarity_score"] for item in results] == pytest.approx([0.9, 0.7])


def test_retriever_preserves_source_provenance():
    record = make_record()
    result = retriever.retrieve_passages(
        "scene", store_loader=lambda: (FakeIndex(), {"records": [record]}), model_loader=FakeModel,
    )[0]
    for field in ("source_id", "translator", "kanda", "source_url", "source_file", "section_id", "text"):
        assert result[field] == record[field]


def test_multi_query_retrieval_deduplicates_and_keeps_best_score():
    shared = make_record("shared-chunk", similarity_score=0.6)
    calls = {"count": 0}

    def fake_retrieve(_query, top_k):
        calls["count"] += 1
        return [dict(shared, similarity_score=0.6 if calls["count"] == 1 else 0.8)]

    ranked, query_results = evidence.retrieve_multiple_queries("Rama in the forest", retrieve_fn=fake_retrieve)
    assert len(query_results) == 3
    assert len(ranked) == 1
    assert ranked[0]["similarity_score"] == 0.8
    assert len(ranked[0]["matched_queries"]) == 3


def test_adjacent_context_has_distinct_role_without_similarity_score():
    primary = make_record("primary", chunk_index=2)
    previous = make_record("previous", chunk_index=1, text="Previous context.")
    following = make_record("following", chunk_index=3, text="Following context.")
    expanded = evidence.expand_with_adjacent_chunks([primary], [previous, primary, following])
    assert [item["chunk_id"] for item in expanded] == ["primary", "previous", "following"]
    assert expanded[0]["retrieval_role"] == "primary"
    assert all(item["retrieval_role"] == "adjacent_context" for item in expanded[1:])
    assert all(item["similarity_score"] is None for item in expanded[1:])
    assert expanded[1]["source_url"] == previous["source_url"]


def test_production_adapter_preserves_contract_provenance_and_metric():
    result = passage_to_contract(dict(make_record(), similarity_score=0.75), rank=1)
    assert result.provenance.translation == config.TRANSLATOR
    assert result.provenance.kanda == "Bāla Kāṇḍa"
    assert str(result.provenance.source_url) == make_record()["source_url"]
    assert result.score_metadata.metric == "inner_product"
    assert result.score_metadata.embedding_normalized is True
