"""Evaluate every generated candidate without hiding any result in a group."""

import unicodedata

from genkavya.contracts.common import CheckStatus, ContractMetadata
from genkavya.contracts.validation import (
    CandidateValidation, ValidationRequest, ValidationResponse,
)

from .grammar import validate_grammar
from .mandatory_words import validate_mandatory_words
from .meter import validate_meter


def validate_generation(request: ValidationRequest) -> ValidationResponse:
    evaluated: list[CandidateValidation] = []
    seen_signatures: set[tuple[str, str, str, str]] = set()
    for rank, candidate in enumerate(request.generation.candidates, 1):
        meter = validate_meter(candidate)
        mandatory = validate_mandatory_words(candidate, request.words)
        grammar_status, grammar_explanation, grammar_tags = validate_grammar(candidate)
        reasons: list[str] = []
        for label, result in (("Meter", meter), ("Mandatory words", mandatory)):
            if result.status == CheckStatus.FAILED:
                reasons.append(f"{label} check failed: {result.explanation or 'required rule failed'}")
            elif result.status == CheckStatus.UNVERIFIED:
                reasons.append(f"{label} check unverified: {result.explanation or 'result could not be established'}")
        signature = tuple(
            " ".join(unicodedata.normalize("NFC", pada).split()) for pada in candidate.padas
        )
        duplicate = signature in seen_signatures
        seen_signatures.add(signature)
        item = CandidateValidation(
            candidate=candidate,
            meter=meter,
            mandatory_words=mandatory,
            grammar_status=grammar_status,
            grammar_explanation=grammar_explanation,
            grammar_warning_tags=grammar_tags,
            rank=rank,
            duplicate_candidate=duplicate,
            invalid_reasons=reasons,
        )
        evaluated.append(item)
    return ValidationResponse(
        candidates=tuple(evaluated),
        metadata=ContractMetadata(producer="genkavya.validation"),
    )


def validate(request: ValidationRequest) -> ValidationResponse:
    return validate_generation(request)
