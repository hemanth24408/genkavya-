import json

import pytest

from genkavya.config import Settings
from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.generation import (
    GenerationRequest, SANSKRIT_CANDIDATE_OUTPUT_SCHEMA, SanskritCandidate,
)
from genkavya.contracts.rag import RagEvidence, RetrievedPassage, SceneRequest, SourceProvenance
from genkavya.contracts.words import FourWordRequest
from genkavya.generation.generator import GenerationError, generate_candidates
from genkavya.validation.mandatory_words import validate_mandatory_words
from genkavya.words.lexicon import load_default_lexicon
from genkavya.words.resolver import resolve_four_words


def request(*, status="success", passages=None, retrieval_role="primary"):
    scene = SceneRequest(scene_description="Rama enters a forest.")
    if passages is None:
        passages = [RetrievedPassage(
            chunk_id="test-chunk", text="Rama enters a forest.",
            provenance=SourceProvenance(kanda="Bāla Kāṇḍa"), rank=1,
            retrieval_role=retrieval_role,
        )]
    evidence = RagEvidence(status=status, query=scene, passages=passages,
                           metadata=ContractMetadata(producer="test-rag"))
    words = resolve_four_words(FourWordRequest(english_words=("forest",) * 4), load_default_lexicon())
    return GenerationRequest(scene=scene, evidence=evidence, words=words)


def payload(padas, summary="A synthetic test candidate."):
    return json.dumps({"padas": padas, "english_summary": summary}, ensure_ascii=False)


def candidate(padas):
    return SanskritCandidate(candidate_id="test", padas=tuple(padas), english_summary="test")


def distinct_payload(label):
    return payload(("वन वन", f"वन {label}", "वन", "रामः"), summary=f"Candidate {label}.")


def test_matcher_remains_exact_standalone_and_duplicate_position_aware():
    req = request()
    assert validate_mandatory_words(candidate(("वन वनम् वने वनानि", "रामः", "वनम्", "वने")), req.words).missing_positions == []
    assert validate_mandatory_words(candidate(("वन", "रामः", "रामः", "रामः")), req.words).missing_positions == [2, 3, 4]
    assert validate_mandatory_words(candidate(("उपवन उपवन", "रामः", "रामः", "रामः")), req.words).missing_positions == [1, 2, 3, 4]


def test_generation_makes_five_single_requests_and_keeps_duplicates_and_missing_words():
    prompts = []
    same = payload(("रामः", "सीता", "लक्ष्मणः", "गच्छति"), "A repeated, word-missing poem.")

    def fake_generate(prompt):
        prompts.append(prompt)
        return same

    result = generate_candidates(
        request(), generate_fn=fake_generate, summary_fn=lambda _: "Short summary.",
        settings=Settings(_env_file=None, generation_max_attempts_per_candidate=3),
    )
    assert len(prompts) == 5
    assert len(result.candidates) == 5
    assert len({tuple(item.padas) for item in result.candidates}) == 1
    assert [item.candidate_id for item in result.candidates] == [f"candidate-{i}" for i in range(1, 6)]
    assert all(f"candidate {i} of 5" in prompt for i, prompt in enumerate(prompts, 1))


def test_malformed_json_is_reported_after_one_request():
    calls = []
    with pytest.raises(GenerationError, match="candidate 1 after one attempt") as raised:
        generate_candidates(
            request(), generate_fn=lambda _: calls.append(1) or "not json",
            summary_fn=lambda _: "Summary.",
            settings=Settings(_env_file=None, generation_max_attempts_per_candidate=3),
        )
    assert calls == [1]
    assert raised.value.attempts == 1
    assert raised.value.failure_stage == "composition"
    assert len(raised.value.attempt_reasons) == 1


def test_invalid_four_pada_structure_is_reported_without_fabricating_or_retrying():
    calls = []
    malformed = payload(("वन", "", "", ""))
    with pytest.raises(GenerationError, match="candidate 1 after one attempt"):
        generate_candidates(
            request(), generate_fn=lambda _: calls.append(1) or malformed,
            summary_fn=lambda _: "Summary.",
            settings=Settings(_env_file=None, generation_max_attempts_per_candidate=3),
        )
    assert calls == [1]


@pytest.mark.parametrize("invalid_payload", [
    payload(("one", "two", "three")),
    payload(("one", "", "three", "four")),
    payload(("one", "two", "three", "four"), summary=""),
])
def test_pydantic_remains_final_structure_validation_after_one_model_response(invalid_payload):
    calls = []
    with pytest.raises(GenerationError, match="candidate 1 after one attempt"):
        generate_candidates(
            request(), generate_fn=lambda _: calls.append(1) or invalid_payload,
            summary_fn=lambda _: "Summary.",
        )
    assert calls == [1]


def test_generator_passes_candidate_schema_to_ollama_once_per_candidate(monkeypatch):
    calls = []
    outputs = iter(distinct_payload(str(i)) for i in range(5))

    def fake_generate(prompt, *, settings, schema):
        calls.append((prompt, schema))
        return next(outputs)

    monkeypatch.setattr("genkavya.generation.generator.generate_json", fake_generate)
    result = generate_candidates(request(), summary_fn=lambda _: "Summary.")
    assert len(result.candidates) == 5
    assert len(calls) == 5
    assert all(schema == SANSKRIT_CANDIDATE_OUTPUT_SCHEMA for _, schema in calls)


def test_summary_is_generated_once_and_five_poetry_requests_receive_all_word_positions():
    summary_prompts, poetry_prompts = [], []
    summary = "Sita sees the deer, and Rama pursues it."

    def summarize(prompt):
        summary_prompts.append(prompt)
        return summary

    outputs = iter(distinct_payload(str(i)) for i in range(5))

    def compose(prompt):
        poetry_prompts.append(prompt)
        return next(outputs)

    result = generate_candidates(request(), summary_fn=summarize, generate_fn=compose)
    assert len(result.candidates) == 5
    assert len(summary_prompts) == 1
    assert len(poetry_prompts) == 5
    assert "Rama enters a forest." in summary_prompts[0]
    for prompt in poetry_prompts:
        assert summary in prompt
        assert "ORIGINAL USER SCENE\nRama enters a forest." in prompt
        for position in range(1, 5):
            assert f'"position":{position}' in prompt
            assert '"english":"forest"' in prompt


def test_unusable_story_summary_fails_before_poetry_requests():
    poetry_calls = []
    with pytest.raises(GenerationError, match="Story summarization failed") as raised:
        generate_candidates(request(), summary_fn=lambda _: "  \n ", generate_fn=lambda p: poetry_calls.append(p))
    assert raised.value.failure_stage == "summarization"
    assert "empty or unusable" in str(raised.value)
    assert poetry_calls == []


def test_missing_primary_context_fails_summary_before_poetry_generation():
    calls = []
    with pytest.raises(GenerationError, match="Story summarization failed") as raised:
        generate_candidates(request(status="insufficient_evidence", passages=[]),
                            generate_fn=lambda p: calls.append(p), summary_fn=lambda _: "ignored")
    assert raised.value.failure_stage == "summarization"
    assert "No primary Ramayana passages" in str(raised.value)
    assert calls == []


@pytest.mark.parametrize("passages", [[], [RetrievedPassage(
    chunk_id="blank-chunk", text=" \t\n ", provenance=SourceProvenance(kanda="Bāla Kāṇḍa"), rank=1,
)]])
def test_no_usable_primary_passage_fails_summary_before_poetry(passages):
    calls = []
    with pytest.raises(GenerationError, match="Story summarization failed"):
        generate_candidates(request(passages=passages), generate_fn=lambda p: calls.append(p),
                            summary_fn=lambda _: "ignored")
    assert calls == []


def test_adjacent_only_evidence_is_not_used_as_primary_for_summary():
    calls = []
    with pytest.raises(GenerationError, match="No primary Ramayana passages"):
        generate_candidates(request(retrieval_role="adjacent_context"), generate_fn=lambda p: calls.append(p),
                            summary_fn=lambda _: "ignored")
    assert calls == []


def test_later_malformed_candidate_preserves_prior_parsed_candidates():
    outputs = [distinct_payload("a"), distinct_payload("b"), "not json"]
    calls = []

    def fake_generate(prompt):
        calls.append(prompt)
        return outputs.pop(0)

    with pytest.raises(GenerationError, match="candidate 3 after one attempt") as raised:
        generate_candidates(request(), generate_fn=fake_generate, summary_fn=lambda _: "Summary.")
    assert len(calls) == 3
    assert len(raised.value.accepted_candidates) == 2
    assert raised.value.failed_candidate_number == 3
    assert raised.value.attempts == 1
    assert len(raised.value.attempt_reasons) == 1
