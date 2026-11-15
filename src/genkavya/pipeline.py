"""Production coordinator for the modular Ramayana-to-poetry workflow.

Run from the project root with ``PYTHONPATH=src python -m genkavya.pipeline
--scene "..." --words word1 word2 word3 word4``. Settings are read through the
existing environment-backed configuration.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from genkavya.config import Settings, get_settings
from genkavya.contracts.generation import GenerationRequest, GenerationResponse
from genkavya.contracts.rag import SceneRequest
from genkavya.contracts.validation import ValidationRequest, ValidationResponse
from genkavya.contracts.words import FourWordRequest
from genkavya.generation.generator import generate_candidates
from genkavya.rag.evidence import retrieve_rag_evidence
from genkavya.validation.validator import validate_generation
from genkavya.words.resolver import resolve_four_words


def run_generation(
    scene_description: str,
    english_words: Sequence[str],
    *,
    settings: Settings | None = None,
) -> GenerationResponse:
    """Run the production workflow and return its established generation contract.

    Use :func:`run_generation_report` when the validation report is also needed.
    """
    generated, _validation = run_generation_report(
        scene_description, english_words, settings=settings
    )
    return generated


def run_generation_report(
    scene_description: str,
    english_words: Sequence[str],
    *,
    settings: Settings | None = None,
) -> tuple[GenerationResponse, ValidationResponse]:
    """Run the workflow and return both existing generation and validation contracts.

    Exceptions from the existing components are allowed to propagate unchanged.
    """
    settings = settings or get_settings()
    scene = SceneRequest(scene_description=scene_description)
    evidence = retrieve_rag_evidence(scene_description)
    words = resolve_four_words(FourWordRequest(english_words=tuple(english_words)))
    request = GenerationRequest(scene=scene, evidence=evidence, words=words)
    generated = generate_candidates(request, settings=settings)
    validation = validate_generation(ValidationRequest(generation=generated, words=words))
    return generated, validation


def _cli_result(generated: GenerationResponse, validation: ValidationResponse) -> dict:
    """Serialize poems and independent evaluation results without an overall verdict."""
    candidate_results = []
    for item in validation.candidates:
        word_check = item.mandatory_words
        word_label = {
            "passed": "ALL WORDS PRESENT",
            "failed": "SOME WORDS MISSING",
            "unverified": "WORD CHECK UNVERIFIED",
        }[word_check.status.value]
        candidate_results.append({
            "candidate_id": item.candidate.candidate_id,
            "padas": list(item.candidate.padas),
            "english_summary": item.candidate.english_summary,
            "duplicate_candidate": item.duplicate_candidate,
            "mandatory_words": {
                "display_status": word_label,
                "status": word_check.status.value,
                "present": [
                    {
                        "input_position": used.input_position,
                        "english": used.input_english,
                        "matched_form_devanagari": used.matched_form_devanagari,
                    }
                    for used in word_check.used_words
                ],
                "missing_positions": word_check.missing_positions,
                "unresolved_positions": word_check.unresolved_positions,
                "explanation": word_check.explanation,
            },
            "meter": item.meter.model_dump(mode="json"),
            # The CLI intentionally exposes only the grammar status.
            "grammar_status": item.grammar_status.value,
        })
    return {
        "generation": generated.model_dump(mode="json"),
        "validation": {
            "metadata": validation.metadata.model_dump(mode="json"),
            "candidates": candidate_results,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and evaluate five GenKavya Sanskrit candidates.")
    parser.add_argument("--scene", required=True, help="English Ramayana scene description")
    parser.add_argument("--words", required=True, nargs=4, metavar=("WORD1", "WORD2", "WORD3", "WORD4"),
                        help="Exactly four English mandatory words in their required order")
    args = parser.parse_args(argv)
    try:
        response, validation = run_generation_report(args.scene, args.words)
    except Exception as exc:
        print(f"GenKavya pipeline failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_cli_result(response, validation), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
