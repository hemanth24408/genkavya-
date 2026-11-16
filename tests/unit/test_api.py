from fastapi.testclient import TestClient

from genkavya import api
from genkavya.contracts.common import ContractMetadata, VerificationStatus
from genkavya.contracts.generation import GenerationResponse, SanskritCandidate
from genkavya.contracts.rag import RagEvidence
from genkavya.contracts.words import WordResolutionStatus
from genkavya import pipeline


client = TestClient(api.app)


def test_generate_endpoint_runs_pipeline_and_returns_existing_report_shape(monkeypatch):
    calls = []
    generated, validation = object(), object()
    result = {"generation": {"candidates": []}, "validation": {"candidates": [{"grammar_status": "unverified"}]}}

    def run(scene, words):
        calls.append((scene, words))
        return generated, validation

    def serialize(actual_generation, actual_validation):
        assert actual_generation is generated
        assert actual_validation is validation
        return result

    monkeypatch.setattr(api, "run_generation_report", run)
    monkeypatch.setattr(api, "serialize_generation_report", serialize)
    response = client.post("/api/generate", json={
        "scene": "A Ramayana scene.",
        "words": ["forest", "flower", "fruit", "mountain"],
    })

    assert response.status_code == 200
    assert response.json() == result
    assert calls == [("A Ramayana scene.", ("forest", "flower", "fruit", "mountain"))]


def test_generate_endpoint_accepts_duplicate_word_positions(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "run_generation_report", lambda scene, words: calls.append(words) or (object(), object()))
    monkeypatch.setattr(api, "serialize_generation_report", lambda *_: {"validation": {"candidates": [{}] * 5}})

    response = client.post("/api/generate", json={"scene": "Scene", "words": ["forest"] * 4})

    assert response.status_code == 200
    assert calls == [("forest",) * 4]


def test_generate_endpoint_resolves_four_production_words_before_generation(monkeypatch):
    scene_words = ("forest", "flower", "fruit", "mountain")
    candidate_set = GenerationResponse(
        candidates=tuple(
            SanskritCandidate(
                candidate_id=f"candidate-{index}",
                padas=("one", "two", "three", "four"),
                english_summary="test summary",
            )
            for index in range(1, 6)
        ),
        metadata=ContractMetadata(producer="test-generation"),
    )
    resolved_records = []

    def generate(request, *, settings):
        resolved_records.extend(request.words.records)
        expected_lemmas = ("वन", "पुष्प", "फल", "पर्वत")
        assert tuple(record.input_english for record in request.words.records) == scene_words
        assert tuple(record.lemma_devanagari for record in request.words.records) == expected_lemmas
        assert all(record.resolution_status == WordResolutionStatus.EXACT for record in request.words.records)
        assert all(record.verification.status == VerificationStatus.VERIFIED for record in request.words.records)
        assert all(
            record.approved_forms
            and all(form.verification.status == VerificationStatus.VERIFIED for form in record.approved_forms)
            for record in request.words.records
        )
        return candidate_set

    monkeypatch.setattr(
        pipeline,
        "retrieve_rag_evidence",
        lambda description: RagEvidence(
            status="success",
            query=pipeline.SceneRequest(scene_description=description),
            metadata=ContractMetadata(producer="test-rag"),
        ),
    )
    monkeypatch.setattr(pipeline, "generate_candidates", generate)
    monkeypatch.setattr(pipeline, "validate_generation", lambda request: object())
    monkeypatch.setattr(api, "serialize_generation_report", lambda *_: {"ok": True})

    response = client.post("/api/generate", json={
        "scene": "A Ramayana scene.",
        "words": list(scene_words),
    })

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(resolved_records) == 4


def test_generate_endpoint_rejects_any_word_count_other_than_four():
    for words in (["forest", "flower", "fruit"], ["forest", "flower", "fruit", "mountain", "river"]):
        response = client.post("/api/generate", json={"scene": "Scene", "words": words})
        assert response.status_code == 422


def test_generate_endpoint_returns_pipeline_errors_as_json(monkeypatch):
    def fail(*_):
        raise RuntimeError("Generation unavailable")

    monkeypatch.setattr(api, "run_generation_report", fail)
    response = client.post("/api/generate", json={"scene": "Scene", "words": ["forest"] * 4})

    assert response.status_code == 502
    assert response.json()["detail"] == "Generation unavailable"
