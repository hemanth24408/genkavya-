import pytest
from pydantic import ValidationError

from genkavya.contracts.rag import RetrievedPassage, RetrievalScoreMetadata, SourceProvenance


def test_existing_faiss_score_metadata_is_explicit_and_unrestricted():
    passage = RetrievedPassage(
        chunk_id="c1", text="passage", rank=1, score=1.27,
        score_metadata=RetrievalScoreMetadata(
            metric="inner_product", embedding_normalized=True,
            interpretation="cosine_similarity_equivalent",
        ),
        provenance=SourceProvenance(kanda="Bāla Kāṇḍa"),
    )
    assert passage.score == 1.27


def test_out_of_scope_kanda_is_rejected():
    with pytest.raises(ValidationError):
        SourceProvenance(kanda="Yuddha Kāṇḍa")

