import json

import pytest
from pydantic import ValidationError

from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.generation import GenerationRequest, GenerationResponse, SanskritCandidate
from genkavya.contracts.rag import RagEvidence, SceneRequest
from genkavya.contracts.words import FourWordRequest
from genkavya.words.lexicon import load_default_lexicon
from genkavya.words.resolver import resolve_four_words


def production_request():
    scene = SceneRequest(scene_description="A requested test scene.")
    evidence = RagEvidence(status="success", query=scene, metadata=ContractMetadata(producer="test-rag"))
    words = resolve_four_words(
        FourWordRequest(english_words=("forest", "forest", "forest", "forest")),
        load_default_lexicon(),
    )
    return GenerationRequest(scene=scene, evidence=evidence, words=words)


def test_candidate_requires_four_nonempty_padas():
    candidate = SanskritCandidate(
        candidate_id="c1", padas=("रामः", "वनम्", "गच्छति", "शुभम्"),
        english_summary="Rama goes to the forest.",
    )
    assert len(candidate.padas) == 4
    assert "mandatory_word" not in SanskritCandidate.model_fields


def test_candidate_rejects_empty_pada():
    with pytest.raises(ValidationError):
        SanskritCandidate(
            candidate_id="c1", padas=("रामः", " ", "गच्छति", "शुभम्"),
            english_summary="summary",
        )


@pytest.mark.parametrize("line_break", ["\n", "\r"])
def test_candidate_rejects_embedded_line_breaks(line_break):
    with pytest.raises(ValidationError, match="single line"):
        SanskritCandidate(
            candidate_id="c1",
            padas=("first", f"second{line_break}continued", "third", "fourth"),
            english_summary="summary",
        )


def test_json_decoded_candidate_with_embedded_newline_is_rejected_by_pydantic():
    payload = json.loads(
        r'{"candidate_id":"c1","padas":["first","second\ncontinued","third","fourth"],"english_summary":"summary"}'
    )
    with pytest.raises(ValidationError, match="single line"):
        SanskritCandidate.model_validate(payload)


def test_generation_request_requires_exactly_five_candidates():
    request = production_request()
    assert request.candidate_count == 5
    for count in (3, 4, 6):
        with pytest.raises(ValidationError, match="Exactly five candidates"):
            GenerationRequest(
                scene=request.scene, evidence=request.evidence, words=request.words,
                candidate_count=count,
            )


def test_generation_response_requires_exactly_five_candidates_but_allows_duplicate_text():
    request = production_request()
    candidates = tuple(SanskritCandidate(
        candidate_id=f"c{i}", padas=("same", "text", "is", "allowed") if i in (0, 1)
        else (f"a{i}", f"b{i}", f"c{i}", f"d{i}"), english_summary="summary"
    ) for i in range(5))
    response = GenerationResponse(candidates=candidates, metadata=ContractMetadata(producer="test"))
    assert len(response.candidates) == 5
    for count in (3, 4, 6):
        with pytest.raises(ValidationError):
            GenerationResponse(
                candidates=tuple(SanskritCandidate(
                    candidate_id=f"count-{count}-{i}", padas=(f"x{i}", f"y{i}", f"z{i}", f"w{i}"),
                    english_summary="summary",
                ) for i in range(count)),
                metadata=response.metadata,
            )
