import pytest

from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.generation import GenerationRequest
from genkavya.contracts.rag import RagEvidence, RetrievedPassage, SceneRequest, SourceProvenance
from genkavya.contracts.words import FourWordRequest
from genkavya.generation.prompt import build_generation_prompt
from genkavya.words.lexicon import load_default_lexicon
from genkavya.words.resolver import resolve_four_words


SCENE = "Rama enters a forest."
SUMMARY = "Rama enters the forest and finds the hermitage."
SECTIONS = (
    "ORIGINAL USER SCENE",
    "RAG STORY SUMMARY",
    "MANDATORY WORDS",
    "POETRY COMPOSITION",
    "PATHYĀ ANUṢṬUBH RULES",
    "OUTPUT FORMAT",
)


def request(*, passages=None, words=("forest",) * 4):
    scene = SceneRequest(scene_description=SCENE)
    evidence = RagEvidence(
        status="success", query=scene, passages=passages or [], metadata=ContractMetadata(producer="test-rag")
    )
    words = resolve_four_words(
        FourWordRequest(english_words=words), load_default_lexicon()
    )
    return GenerationRequest(scene=scene, evidence=evidence, words=words)


def passage(chunk_id, role, rank, text):
    return RetrievedPassage(
        chunk_id=chunk_id,
        text=text,
        provenance=SourceProvenance(kanda="Bāla Kāṇḍa"),
        rank=rank,
        retrieval_role=role,
    )


def test_prompt_has_only_the_five_required_sections_and_uses_story_summary():
    req = request(passages=[
        passage("primary-1", "primary", 1, "Primary passage text."),
        passage("adjacent-1", "adjacent_context", 2, "Adjacent context text."),
    ])
    prompt = build_generation_prompt(req, story_summary=SUMMARY)
    headings = tuple(line for line in prompt.splitlines() if line in SECTIONS)
    assert headings == SECTIONS
    assert SUMMARY in prompt
    assert f"ORIGINAL USER SCENE\n{SCENE}" in prompt
    assert f"RAG STORY SUMMARY\n{SUMMARY}" in prompt
    assert "primary-1" not in prompt
    assert "adjacent-1" not in prompt
    assert "Adjacent context text." not in prompt


def test_all_four_duplicate_positions_and_all_verified_approved_forms_are_present():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    for position in range(1, 5):
        assert f'"position":{position}' in prompt
        assert '"english":"forest"' in prompt
    for form in ("वन", "वनम्", "वने", "वनानि"):
        assert f'"devanagari":"{form}"' in prompt
    assert "copy at least one listed Devanagari spelling exactly" in prompt
    assert "Each token occurrence can satisfy only one position" in prompt
    assert "grammatically suitable listed form" in prompt
    assert "Do not use approximate spellings, unapproved inflections, synonyms" in prompt
    assert "complete standalone token separated from neighboring text by whitespace" in prompt
    assert "appearing only in the English summary does not count" in prompt


def test_exact_approved_forms_are_prominent_and_require_literal_standalone_spelling():
    prompt = build_generation_prompt(
        request(words=("forest", "flower", "fruit", "mountain")), story_summary=SUMMARY
    )
    assert "POSITION 1 — forest: वन | वनम् | वने | वनानि" in prompt
    assert "POSITION 2 — flower: पुष्प | पुष्पम् | पुष्पे | पुष्पाणि" in prompt
    assert "POSITION 3 — fruit: फल | फलम् | फले | फलानि" in prompt
    assert "POSITION 4 — mountain: पर्वत | पर्वतः | पर्वतम् | पर्वते | पर्वताः" in prompt
    assert "copy at least one listed Devanagari spelling exactly, including its ending" in prompt
    assert "anusvāra/visarga distinction" in prompt
    assert "PRESERVE EVERY DEVANAGARI CHARACTER EXACTLY" in prompt
    assert "Dental न and retroflex ण are different" in prompt
    assert "पुष्पाणि is approved; पुष्पानि is not" in prompt
    assert "Use only the listed approved forms; do not respell or independently inflect them" in prompt
    assert "complete standalone token separated from neighboring text by whitespace" in prompt
    assert "Do not use approximate spellings, unapproved inflections, synonyms, compounds, or sandhi transformations" in prompt
    assert "confirm that every one of the four positions has at least one exact standalone occurrence" in prompt


def test_meter_rules_are_exact_and_no_extra_restrictions_are_added():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "exactly four non-empty padas" in prompt
    assert "exactly eight metrical syllables in each (32 total)" in prompt
    assert "____LGG_" in prompt
    assert "____LGL_" in prompt
    assert "Metrical syllables are not written characters" in prompt
    assert "short vowel is generally Laghu" in prompt
    assert "long vowel is generally Guru" in prompt
    assert "add no other classical restrictions" in prompt
    assert "independent Validator is the final authority" in prompt
    assert "one word per pada" not in prompt.casefold()
    assert "one-word-per-pada" not in prompt.casefold()


def test_output_contract_and_five_candidate_process_remain_explicit():
    prompt = build_generation_prompt(
        request(),
        candidate_number=2,
        previous_candidates=(("वन वन", "वन", "वन", "रामः"),),
        retry_feedback="Input position 4 is missing.",
        story_summary=SUMMARY,
    )
    assert "Generate exactly five meaningfully distinct candidates across the full process" in prompt
    assert "candidate 2 of 5" in prompt
    assert '"padas"' in prompt and '"english_summary"' in prompt
    assert "four non-empty padas" in prompt
    assert "वन वन" in prompt
    assert "Retry feedback: Input position 4 is missing." in prompt


def test_prompt_requires_each_pada_string_to_be_one_line():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "exactly four strings" in prompt
    assert "each string represents exactly one pāda on exactly one line" in prompt
    assert "Do not include `\\n` or `\\r` characters inside a pada" in prompt
    assert "Do not combine multiple padas into one string" in prompt
    assert "use line breaks to separate phrases within a pada" in prompt
    assert '"padas"' in prompt and '"english_summary"' in prompt


def test_prompt_requires_scene_faithfulness_and_summary_to_match_the_verse():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "The Sanskrit padas themselves must communicate a meaningful connection to the requested scene" in prompt
    assert "the English summary is not a substitute" in prompt
    assert "English summary describe what the Sanskrit verse actually expresses" in prompt
    assert "explain its connection to the scene" in prompt


def test_prompt_encourages_direct_symbolic_and_layered_avadhani_interpretations():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "(A) directly express one meaningful event, action, relationship, or moment" in prompt
    assert "(B) symbolically represent the scene" in prompt
    assert "(C) layer an imaginative surface image with a deeper meaning" in prompt
    assert "Different candidates may use different approaches" in prompt
    assert "do not force all three into one style" in prompt


def test_prompt_uses_mandatory_words_as_poetic_elements_and_explains_symbolic_summary():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "Let the four mandatory words help shape one coherent poetic idea" in prompt
    assert "their literal or symbolic meanings, imagery, wordplay, or relationships" in prompt
    assert "Do not interpret every word literally" in prompt
    assert "create an arbitrary metaphor merely to include the words" in prompt
    assert "make the English summary describe what the Sanskrit verse actually expresses" in prompt
    assert "including a deeper meaning when the verse is symbolic or layered" in prompt
    assert "Do not use the original scene to invent meaning for an unclear verse" in prompt


def test_candidate_diversity_requires_a_new_central_idea_and_uses_prior_candidates():
    previous = (("पूर्वपद्यस्य प्रथमपादः", "द्वितीयः", "तृतीयः", "चतुर्थः"),)
    prompt = build_generation_prompt(
        request(), candidate_number=2, previous_candidates=previous, story_summary=SUMMARY
    )
    assert "study the previously generated candidates shown below" in prompt
    assert "meaningfully different central poetic idea, image, relationship, or interpretation" in prompt
    assert "Avoid reusing their central imagery, metaphors, sentence structures, and poetic approach" in prompt
    assert "Changing only a few words does not make a new composition" in prompt
    assert "पूर्वपद्यस्य प्रथमपादः" in prompt


def test_mandatory_words_shape_one_coherent_idea_without_fixed_distribution():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "All four must contribute meaningfully to that idea" in prompt
    assert "Place them naturally and flexibly across the padas" in prompt
    assert "do not automatically put all four in the first pada" in prompt
    assert "treat them as a checklist to finish before composing" in prompt
    assert "Do not force one mandatory word into each pada" in prompt
    assert "one word per pada" not in prompt.casefold()


def test_english_summary_is_based_on_poem_and_does_not_invent_scene_details():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "First determine what the four Sanskrit padas actually communicate" in prompt
    assert "write the English summary from that meaning" in prompt
    assert "explain the symbolic mapping actually expressed" in prompt
    assert "Do not add characters, actions, events, or details that the Sanskrit does not communicate" in prompt
    assert "Do not use the original scene to invent meaning for an unclear verse" in prompt
    assert "Describe an indirect connection honestly without overstating it" in prompt


def test_prompt_selects_one_scene_moment_and_limits_story_content():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "Do NOT narrate or summarize the entire supplied story in one verse" in prompt
    assert "select ONE meaningful central moment, action, or event" in prompt
    assert "A candidate need not include every character, action, event, or detail" in prompt
    assert "different candidates may focus on different moments" in prompt
    assert "Mārīcha's disguise, Sītā seeing the deer, or Rāma pursuing it" in prompt
    assert "First determine what the four Sanskrit padas actually communicate" in prompt


def test_prompt_prioritizes_concise_padas_without_weakening_meter():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "32 metrical syllables; treat this as a strict space limit" in prompt
    assert "Express only the essential idea of the selected moment" in prompt
    assert "Do not lengthen a pada to include more information" in prompt
    assert "never sacrifice the eight-syllable requirement" in prompt
    assert "exactly eight metrical syllables in each (32 total)" in prompt
    assert "____LGG_" in prompt and "____LGL_" in prompt


def test_prompt_requests_short_meter_first_composition_and_natural_word_distribution():
    prompt = build_generation_prompt(request(), story_summary=SUMMARY)
    assert "plan four short padas" in prompt
    assert "First understand the story" in prompt
    assert "Place them naturally and flexibly across the padas" in prompt
    assert "correct case, gender, number, and agreement" in prompt


def test_direct_prompt_call_without_summary_remains_compatible():
    prompt = build_generation_prompt(request())
    assert SCENE in prompt
    assert f"ORIGINAL USER SCENE\n{SCENE}" in prompt
    assert "RAG STORY SUMMARY" in prompt
    assert tuple(line for line in prompt.splitlines() if line in SECTIONS) == SECTIONS


def test_prompt_rejects_candidate_number_above_five():
    with pytest.raises(ValueError, match="between 1 and 5"):
        build_generation_prompt(request(), candidate_number=6, story_summary=SUMMARY)
