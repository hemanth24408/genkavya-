import pytest

from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.generation import GenerationRequest
from genkavya.contracts.rag import RagEvidence, RetrievedPassage, SceneRequest, SourceProvenance
from genkavya.contracts.words import FourWordRequest
from genkavya.generation.summarizer import (
    StorySummaryError,
    build_story_summary_prompt,
    summarize_story,
)
from genkavya.words.lexicon import load_default_lexicon
from genkavya.words.resolver import resolve_four_words


def request():
    scene = SceneRequest(scene_description="Sita sees the golden deer and asks Rama to pursue it.")
    passages = [
        RetrievedPassage(
            chunk_id="primary-rank-3",
            text="A third ranked primary account.",
            provenance=SourceProvenance(kanda="Araṇya Kāṇḍa"),
            rank=3,
            retrieval_role="primary",
        ),
        RetrievedPassage(
            chunk_id="adjacent-rank-1",
            text="Adjacent context must not be included as primary.",
            provenance=SourceProvenance(kanda="Araṇya Kāṇḍa"),
            rank=1,
            retrieval_role="adjacent_context",
        ),
        RetrievedPassage(
            chunk_id="primary-rank-1",
            text="Sita beholds the golden deer and asks Rama to obtain it.",
            provenance=SourceProvenance(kanda="Araṇya Kāṇḍa"),
            rank=1,
            retrieval_role="primary",
        ),
        RetrievedPassage(
            chunk_id="primary-rank-2",
            text="Rama pursues the deer while Lakshmana warns of Maricha's illusion.",
            provenance=SourceProvenance(kanda="Araṇya Kāṇḍa"),
            rank=2,
            retrieval_role="primary",
        ),
    ]
    evidence = RagEvidence(
        status="success", query=scene, passages=passages, metadata=ContractMetadata(producer="test-rag")
    )
    words = resolve_four_words(
        FourWordRequest(english_words=("forest",) * 4), load_default_lexicon()
    )
    return GenerationRequest(scene=scene, evidence=evidence, words=words)


def test_summary_prompt_uses_two_highest_ranked_primary_passages_only():
    prompt = build_story_summary_prompt(request())
    assert "Sita sees the golden deer and asks Rama to pursue it." in prompt
    assert '"passage_id": "primary-rank-1"' in prompt
    assert '"passage_id": "primary-rank-2"' in prompt
    assert "Sita beholds the golden deer and asks Rama to obtain it." in prompt
    assert "Rama pursues the deer while Lakshmana warns" in prompt
    assert "primary-rank-3" not in prompt
    assert "adjacent-rank-1" not in prompt
    assert "Adjacent context must not be included as primary" not in prompt
    assert "Return plain text only, with no JSON" in prompt


def test_summary_generation_returns_short_plain_text_trimmed():
    prompts = []
    expected = "Sita sees a golden deer, and Rama pursues it."

    def fake_generate(prompt):
        prompts.append(prompt)
        return "  " + expected + "\n"

    result = summarize_story(request(), generate_fn=fake_generate)
    assert result.rag_summary == expected
    assert result.original_scene == request().scene.scene_description
    assert len(prompts) == 1


@pytest.mark.parametrize("response", ["", " \n\t ", "!!!", "{\"summary\": \"\"}", "{\"result\": {}}"])
def test_empty_or_unusable_summary_is_rejected(response):
    with pytest.raises(StorySummaryError, match="empty|plain-text"):
        summarize_story(request(), generate_fn=lambda _prompt: response)


def test_json_wrapped_summary_extracts_useful_english_text():
    response = '{"summary": "Sita sees the deer, and Rama pursues it."}'
    result = summarize_story(request(), generate_fn=lambda _prompt: response)
    assert result.rag_summary == "Sita sees the deer, and Rama pursues it."
    assert result.original_scene == request().scene.scene_description


def test_json_with_summary_in_key_uses_nonempty_english_key_as_fallback():
    response = '{"Sita sees the deer, and Rama pursues it.": "", "metadata": {}}'
    result = summarize_story(request(), generate_fn=lambda _prompt: response)
    assert result.rag_summary == "Sita sees the deer, and Rama pursues it."


def test_key_wrapped_qwen_summary_prefers_concise_useful_text():
    response = (
        '{"Maricha transforms into a golden deer to lure Rama and Lakshmana away. '
        'Sita is left alone and Ravana abducts her.": "", '
        '"Sita sees the golden deer; Rama pursues it, leaving her alone for Ravana.": {}}'
    )
    result = summarize_story(request(), generate_fn=lambda _prompt: response)
    assert result.rag_summary == "Sita sees the golden deer; Rama pursues it, leaving her alone for Ravana."


def test_no_primary_passages_fails_clearly():
    req = request()
    req.evidence.passages = [p for p in req.evidence.passages if p.retrieval_role != "primary"]
    with pytest.raises(StorySummaryError, match="No primary Ramayana passages"):
        summarize_story(req, generate_fn=lambda _prompt: "unused")
