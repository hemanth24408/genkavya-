"""Concise prompt construction for Sanskrit padyam generation."""

from __future__ import annotations

import json

from genkavya.contracts.common import VerificationStatus
from genkavya.contracts.generation import GenerationRequest


def _approved_word_data(request: GenerationRequest) -> list[dict]:
    """Return all verified approved forms, grouped by the four input positions."""
    positions = []
    for record in request.words.records:
        forms = []
        for form in record.approved_forms:
            if form.verification.status != VerificationStatus.VERIFIED:
                continue
            grammar = {
                key: value
                for key, value in form.grammar.model_dump(exclude_none=True).items()
                if value not in (None, {}, [])
            }
            forms.append({"devanagari": form.form_devanagari, "kind": form.kind.value, "grammar": grammar})
        positions.append({
            "position": record.input_position,
            "english": record.input_english,
            "lemma": record.lemma_devanagari,
            "approved_forms": forms,
        })
    return positions


def select_primary_passages(request: GenerationRequest) -> list[dict]:
    """Choose up to two non-empty primary passages by RAG rank (lower is better)."""
    passages = [
        passage for passage in request.evidence.passages
        if passage.retrieval_role == "primary" and passage.text.strip()
    ]
    passages.sort(key=lambda passage: (
        passage.rank,
        -(passage.score if passage.score is not None else float("-inf")),
    ))
    return [
        {
            "passage_id": passage.chunk_id,
            "rank": passage.rank,
            "score": passage.score,
            "score_metadata": passage.score_metadata.model_dump(exclude_none=True) if passage.score_metadata else None,
            "source_information": passage.provenance.model_dump(mode="json", exclude_none=True),
            "text": passage.text,
        }
        for passage in passages[:2]
    ]


def build_generation_prompt(
    request: GenerationRequest,
    *,
    candidate_number: int = 1,
    previous_candidates: tuple[tuple[str, str, str, str], ...] = (),
    retry_feedback: str = "",
    story_summary: str | None = None,
    original_scene: str | None = None,
) -> str:
    """Build a five-section prompt with separate user-scene and RAG-summary context."""
    if not 1 <= candidate_number <= 5:
        raise ValueError("candidate_number must be between 1 and 5")

    original_scene = request.scene.scene_description if original_scene is None else original_scene
    rag_summary = story_summary.strip() if story_summary is not None else ""
    approved_words = _approved_word_data(request)
    word_data = json.dumps(approved_words, ensure_ascii=False, separators=(",", ":"))
    approved_word_lines = "\n".join(
        f"POSITION {item['position']} — {item['english']}: "
        + " | ".join(form["devanagari"] for form in item["approved_forms"])
        for item in approved_words
    )
    earlier = json.dumps([list(candidate) for candidate in previous_candidates], ensure_ascii=False, separators=(",", ":"))
    feedback = f"\nRetry feedback: {retry_feedback.strip()}" if retry_feedback.strip() else ""

    return f"""ORIGINAL USER SCENE
{original_scene}

RAG STORY SUMMARY
{rag_summary if rag_summary else original_scene}
Consider both the user's intended scene and this supporting Ramayana context when composing poetry.
Understand the characters, actions, event order, and relationships. The Sanskrit padas themselves must communicate a meaningful connection to the requested scene; the English summary is not a substitute. A verse may connect indirectly through a clear symbolic or layered interpretation, even without naming the original characters. Preserve the scene's essential meaning, avoid unsupported events or characters, and make the English summary describe what the Sanskrit verse actually expresses and explain its connection to the scene, including a deeper meaning when the verse is symbolic or layered. If the scene concerns the golden deer, possible meaningful moments include Mārīcha's disguise, Sītā seeing the deer, or Rāma pursuing it; these are examples, not required assignments.

MANDATORY WORDS
COPY-EXACT APPROVED SPELLINGS BY INPUT POSITION
{approved_word_lines}
{word_data}
PRESERVE EVERY DEVANAGARI CHARACTER EXACTLY. Dental न and retroflex ण are different: for flower, पुष्पाणि is approved; पुष्पानि is not. Use only the listed approved forms; do not respell or independently inflect them.
All four input positions are independent requirements. For each position, copy at least one listed Devanagari spelling exactly, including its ending and any anusvāra/visarga distinction. Each required form must appear as a complete standalone token separated from neighboring text by whitespace. Each token occurrence can satisfy only one position. Choose a grammatically suitable listed form. Do not use approximate spellings, unapproved inflections, synonyms, compounds, or sandhi transformations, and do not attach a required form to neighboring text. Distribute the words naturally across the padas.
Before returning JSON, inspect the Sanskrit padas themselves and confirm that every one of the four positions has at least one exact standalone occurrence of one of its own listed forms. An approximate spelling, a form embedded in a compound or attached to another word, or a word appearing only in the English summary does not count. If any position is missing, revise the padas before responding.

POETRY COMPOSITION
First understand the story and complete scene, then select ONE meaningful central moment, action, or event. Do NOT narrate or summarize the entire supplied story in one verse. Then plan four short padas built around the selected moment. A candidate need not include every character, action, event, or detail from the scene or RAG summary. Expressing one meaningful part clearly and beautifully is better than forcing the whole story into an excessively long verse.

Let the four mandatory words help shape one coherent poetic idea. All four must contribute meaningfully to that idea through their literal or symbolic meanings, imagery, wordplay, or relationships. Place them naturally and flexibly across the padas; do not automatically put all four in the first pada or treat them as a checklist to finish before composing. Do not force one mandatory word into each pada. The padas should read as one connected composition, not unrelated lines. Do not interpret every word literally, force Ramayana names into every verse, or create an arbitrary metaphor merely to include the words.

Choose one approach for each candidate: (A) directly express one meaningful event, action, relationship, or moment from the scene; (B) symbolically represent the scene through meaningful metaphor, imagery, comparison, wordplay, or relationships among the mandatory words; or (C) layer an imaginative surface image with a deeper meaning connected to the scene. Different candidates may use different approaches; do not force all three into one style. Each verse must communicate its idea and a meaningful scene connection.

Before composing each new candidate, study the previously generated candidates shown below. Choose a meaningfully different central poetic idea, image, relationship, or interpretation. Avoid reusing their central imagery, metaphors, sentence structures, and poetic approach. Changing only a few words does not make a new composition. Explore a different meaningful relationship between the mandatory words and the scene while keeping the verse coherent.

First determine what the four Sanskrit padas actually communicate, then write the English summary from that meaning. Explain how it connects to the original Ramayana scene and, for symbolic or layered poetry, explain the symbolic mapping actually expressed. Do not add characters, actions, events, or details that the Sanskrit does not communicate. Do not use the original scene to invent meaning for an unclear verse. Describe an indirect connection honestly without overstating it; the summary must describe the poem, not independently retell the Ramayana scene.

The verse has only four padas and 32 metrical syllables; treat this as a strict space limit. Express only the essential idea of the selected moment. Prefer short, simple, natural Sanskrit constructions. Avoid unnecessary descriptions, repeated ideas, and extra story details. Do not lengthen a pada to include more information, and never sacrifice the eight-syllable requirement to express more of the story.

Compose in Devanagari using familiar vocabulary and straightforward sentence construction. Use correct case, gender, number, and agreement. Avoid obscure vocabulary, meaningless words, invented forms, unnecessary compounds, and unnatural word order. Fit the required words naturally without assigning one word to each pada. Make the five candidates meaningfully different in wording and sentence construction while preserving the same story. When appropriate, different candidates may focus on different moments from the scene; for the golden deer scene, candidates may focus on Mārīcha's disguise, Sītā seeing the deer, or Rāma pursuing it. These are examples, not fixed assignments. Avoid superficial variations that only replace one word with another.

PATHYĀ ANUṢṬUBH RULES
Meter is a required composition constraint. Return exactly four non-empty padas, with exactly eight metrical syllables in each (32 total). Metrical syllables are not written characters: consider vowel length and syllable boundaries; never count Devanagari characters as syllables. Laghu (L) is a light syllable and Guru (G) is a heavy syllable. A short vowel is generally Laghu unless Sanskrit prosody makes it heavy; a long vowel is generally Guru. Anusvāra, visarga, consonant clusters, or syllable closure can make a preceding short-vowel syllable Guru.

Required positions 5–7:
- Padas 1 and 3: `____LGG_` (L–G–G).
- Padas 2 and 4: `____LGL_` (L–G–L).

After composing, check each pada's syllable count and required cadence. Revise its wording if either is wrong, while preserving natural Sanskrit, grammar, and story meaning. Apply only these project-specific meter rules; add no other classical restrictions. The independent Validator is the final authority, and you must not claim that a candidate has passed validation.

OUTPUT FORMAT
Generate exactly five meaningfully distinct candidates across the full process. This is candidate {candidate_number} of 5. Use a different central idea from earlier candidates where possible: {earlier}.{feedback}
The `padas` array must contain exactly four strings, and each string represents exactly one pāda on exactly one line. Do not include `\\n` or `\\r` characters inside a pada. Do not combine multiple padas into one string or use line breaks to separate phrases within a pada.
Return only this JSON object: {{"padas":["pāda 1","pāda 2","pāda 3","pāda 4"],"english_summary":"concise English meaning"}}. Include exactly four non-empty single-line padas and an English summary. Do not add fields or claim validation."""
