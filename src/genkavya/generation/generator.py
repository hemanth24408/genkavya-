"""Generate five parsed candidates with one composition request per candidate."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from genkavya.config import Settings, get_settings
from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.generation import (
    GenerationRequest,
    GenerationResponse,
    SANSKRIT_CANDIDATE_OUTPUT_SCHEMA,
    SanskritCandidate,
)

from .ollama import generate_json
from .prompt import build_generation_prompt
from .summarizer import StorySummaryError, summarize_story


class GenerationError(RuntimeError):
    """Generation failed, with any accepted candidates retained for inspection."""

    def __init__(
        self,
        message: str,
        *,
        accepted_candidates: tuple[SanskritCandidate, ...] = (),
        failed_candidate_number: int | None = None,
        attempts: int | None = None,
        attempt_reasons: tuple[str, ...] = (),
        failure_stage: str = "composition",
        retry_limit: int | None = None,
    ) -> None:
        super().__init__(message)
        self.accepted_candidates = accepted_candidates
        self.failed_candidate_number = failed_candidate_number
        self.attempts = attempts
        self.attempt_reasons = attempt_reasons
        self.failure_stage = failure_stage
        self.retry_limit = retry_limit


def _candidate_from_payload(payload: Any, candidate_number: int) -> SanskritCandidate:
    if not isinstance(payload, dict):
        raise ValueError("Model response must be a JSON object")
    # The ID is assigned by the service and is not generated or trusted from model output.
    candidate_data = dict(payload)
    candidate_data["candidate_id"] = f"candidate-{candidate_number}"
    return SanskritCandidate.model_validate(candidate_data)


def _signature(candidate: SanskritCandidate) -> tuple[str, str, str, str]:
    return tuple(" ".join(unicodedata.normalize("NFC", pada).split()) for pada in candidate.padas)  # type: ignore[return-value]


def generate_candidates(
    request: GenerationRequest,
    *,
    generate_fn: Callable[[str], str] | None = None,
    summary_fn: Callable[[str], str] | None = None,
    settings: Settings | None = None,
) -> GenerationResponse:
    """Return five structurally parsed candidates; evaluation is handled downstream."""
    settings = settings or get_settings()
    call_model = generate_fn or (
        lambda prompt: generate_json(
            prompt, settings=settings, schema=SANSKRIT_CANDIDATE_OUTPUT_SCHEMA
        )
    )
    try:
        story_summary = summarize_story(
            request,
            generate_fn=summary_fn,
            settings=settings,
        )
    except StorySummaryError as exc:
        reason = str(exc)
        raise GenerationError(
            f"Story summarization failed; poetry generation was not started: {reason}",
            accepted_candidates=(),
            attempt_reasons=(reason,),
            failure_stage="summarization",
            retry_limit=1,
        ) from exc

    candidates: list[SanskritCandidate] = []
    for candidate_number in range(1, 6):
        prompt = build_generation_prompt(
            request,
            candidate_number=candidate_number,
            previous_candidates=tuple(_signature(candidate) for candidate in candidates),
            story_summary=story_summary.rag_summary,
            original_scene=story_summary.original_scene,
        )
        try:
            raw = call_model(prompt)
            payload = json.loads(raw)
            candidate = _candidate_from_payload(payload, candidate_number)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise GenerationError(
                f"Could not parse candidate {candidate_number} after one attempt: {exc}",
                accepted_candidates=tuple(candidates),
                failed_candidate_number=candidate_number,
                attempts=1,
                attempt_reasons=(str(exc),),
                failure_stage="composition",
                retry_limit=1,
            ) from exc
        candidates.append(candidate)

    return GenerationResponse(
        candidates=tuple(candidates),
        metadata=ContractMetadata(producer="genkavya.generation"),
    )
