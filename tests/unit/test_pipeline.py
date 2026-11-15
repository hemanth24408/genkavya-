import pytest

from genkavya.config import Settings
from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.generation import GenerationResponse, SanskritCandidate
from genkavya.contracts.rag import RagEvidence, SceneRequest
from genkavya.contracts.words import FourWordRequest
from genkavya.pipeline import main, run_generation
from genkavya.words.lexicon import load_default_lexicon
from genkavya.words.resolver import resolve_four_words


def fixtures():
    scene = SceneRequest(scene_description="A scene.")
    evidence = RagEvidence(status="success", query=scene, metadata=ContractMetadata(producer="test-rag"))
    candidates = tuple(
        SanskritCandidate(
            candidate_id=f"c{i}", padas=(f"a{i}", f"b{i}", f"c{i}", f"d{i}"), english_summary="summary"
        )
        for i in range(1, 6)
    )
    generation = GenerationResponse(candidates=candidates, metadata=ContractMetadata(producer="test-generation"))
    return scene, evidence, generation


def test_coordinator_runs_components_in_order_preserving_duplicate_positions(monkeypatch):
    scene, evidence, generation = fixtures()
    calls = []
    settings = Settings(ollama_model="qwen2.5:7b")

    def retrieve(text):
        calls.append(("rag", text))
        return evidence

    def resolve(request):
        calls.append(("words", request.english_words))
        return resolve_four_words(request, load_default_lexicon())

    def generate(request, *, settings):
        calls.append(("generation", request, settings))
        return generation

    monkeypatch.setattr("genkavya.pipeline.retrieve_rag_evidence", retrieve)
    monkeypatch.setattr("genkavya.pipeline.resolve_four_words", resolve)
    monkeypatch.setattr("genkavya.pipeline.generate_candidates", generate)
    # The validator is mocked as a component boundary; its response is not consumed here.
    monkeypatch.setattr("genkavya.pipeline.validate_generation", lambda request: calls.append(("validation", request.generation, request.words)))
    words = ("forest", "forest", "fruit", "mountain")
    result = run_generation("A scene.", words, settings=settings)

    assert result is generation
    assert [call[0] for call in calls] == ["rag", "words", "generation", "validation"]
    assert calls[1][1] == words
    assert calls[2][1].scene == scene
    assert calls[2][1].evidence is evidence
    assert calls[2][2] is settings
    assert calls[3][1] is generation


@pytest.mark.parametrize("failing_component", ["rag", "words", "generation", "validation"])
def test_coordinator_propagates_component_errors(monkeypatch, failing_component):
    _, evidence, generation = fixtures()
    error = RuntimeError(f"{failing_component} failed")

    def maybe_fail(name, result):
        def call(*args, **kwargs):
            if name == failing_component:
                raise error
            return result
        return call

    monkeypatch.setattr("genkavya.pipeline.retrieve_rag_evidence", maybe_fail("rag", evidence))
    resolved = resolve_four_words(
        FourWordRequest(english_words=("forest", "flower", "fruit", "mountain")),
        load_default_lexicon(),
    )
    monkeypatch.setattr("genkavya.pipeline.resolve_four_words", maybe_fail("words", resolved))
    monkeypatch.setattr("genkavya.pipeline.generate_candidates", maybe_fail("generation", generation))
    monkeypatch.setattr("genkavya.pipeline.validate_generation", maybe_fail("validation", None))

    with pytest.raises(RuntimeError) as raised:
        run_generation("A scene.", ("forest", "flower", "fruit", "mountain"))
    assert raised.value is error


def test_cli_json_includes_per_candidate_evaluation_without_overall_verdict(monkeypatch, capsys):
    _, _, generation = fixtures()
    candidates = list(generation.candidates)
    candidates[1] = candidates[1].model_copy(update={"padas": candidates[0].padas})
    generation = GenerationResponse(candidates=tuple(candidates), metadata=generation.metadata)
    words = resolve_four_words(
        FourWordRequest(english_words=("forest", "flower", "fruit", "mountain")),
        load_default_lexicon(),
    )
    from genkavya.contracts.validation import ValidationRequest
    from genkavya.validation.validator import validate_generation

    validation = validate_generation(ValidationRequest(generation=generation, words=words))
    monkeypatch.setattr(
        "genkavya.pipeline.run_generation_report",
        lambda scene, inputs: (generation, validation),
    )

    assert main(["--scene", "A scene.", "--words", "forest", "flower", "fruit", "mountain"]) == 0
    import json

    payload = json.loads(capsys.readouterr().out)
    assert payload["generation"]["candidates"]
    assert len(payload["validation"]["candidates"]) == 5
    result = payload["validation"]["candidates"][0]
    assert result["mandatory_words"]["display_status"] in {
        "ALL WORDS PRESENT", "SOME WORDS MISSING", "WORD CHECK UNVERIFIED",
    }
    assert "missing_positions" in result["mandatory_words"]
    assert "syllable_counts" in result["meter"]
    assert "checks" in result["meter"]
    assert result["grammar_status"] in {"verified", "issues_found", "unverified"}
    assert "grammar_explanation" not in result
    assert "classification" not in result
    assert payload["validation"]["candidates"][1]["duplicate_candidate"] is True
    assert payload["validation"]["candidates"][0]["duplicate_candidate"] is False
    assert result["meter"] == validation.candidates[0].meter.model_dump(mode="json")
    assert result["grammar_status"] == validation.candidates[0].grammar_status.value

