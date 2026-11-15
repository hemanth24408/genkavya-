"""Exact approved-form matching for the four original word positions."""

from __future__ import annotations

import re
import unicodedata

from genkavya.contracts.common import CheckStatus, VerificationStatus
from genkavya.contracts.generation import SanskritCandidate
from genkavya.contracts.validation import MandatoryWordValidation, UsedWord
from genkavya.contracts.words import FourWordResolution, WordResolutionStatus


_TOKEN_SPLIT = re.compile(r"[\s।॥,;:!?]+")


def _tokens(pada: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", pada)
    return [token.strip("\"'“”‘’()[]{}") for token in _TOKEN_SPLIT.split(normalized) if token.strip("\"'“”‘’()[]{}")] 


def validate_mandatory_words(candidate: SanskritCandidate, words: FourWordResolution) -> MandatoryWordValidation:
    """Assign distinct exact token occurrences to input positions using only verified forms."""
    records = words.records
    required = tuple(record.input_english for record in records)
    occurrences: list[tuple[int, int, str]] = []
    for pada_number, pada in enumerate(candidate.padas, 1):
        occurrences.extend((pada_number, index, token) for index, token in enumerate(_tokens(pada)))

    eligible: dict[int, list[int]] = {}
    unresolved_positions: list[int] = []
    for position, record in enumerate(records, 1):
        if record.resolution_status != WordResolutionStatus.EXACT:
            unresolved_positions.append(position)
            eligible[position] = []
            continue
        forms = {
            unicodedata.normalize("NFC", form.form_devanagari)
            for form in record.approved_forms
            if form.verification.status == VerificationStatus.VERIFIED
        }
        eligible[position] = [i for i, (_, _, token) in enumerate(occurrences) if token in forms]

    # Maximum bipartite matching: duplicate input positions need distinct token occurrences.
    occurrence_to_position: dict[int, int] = {}

    def assign(position: int, seen: set[int]) -> bool:
        for occurrence in eligible[position]:
            if occurrence in seen:
                continue
            seen.add(occurrence)
            if occurrence not in occurrence_to_position or assign(occurrence_to_position[occurrence], seen):
                occurrence_to_position[occurrence] = position
                return True
        return False

    for position in range(1, len(records) + 1):
        if position not in unresolved_positions:
            assign(position, set())

    position_to_occurrence = {position: occurrence for occurrence, position in occurrence_to_position.items()}
    used: list[UsedWord] = []
    for position, occurrence_index in sorted(position_to_occurrence.items()):
        record = records[position - 1]
        pada_number, token_index, token = occurrences[occurrence_index]
        matched_form = next(
            form for form in record.approved_forms
            if form.verification.status == VerificationStatus.VERIFIED
            and unicodedata.normalize("NFC", form.form_devanagari) == token
        )
        used.append(UsedWord(
            input_position=position,
            input_english=record.input_english,
            matched_form_devanagari=matched_form.form_devanagari,
            base_lemma_id=matched_form.base_lemma_id,
            stem_id=matched_form.stem_id,
            form_kind=matched_form.kind,
            pada_numbers=[pada_number],
            token_index=token_index,
        ))

    used_positions = {item.input_position for item in used}
    missing_positions = [
        position for position in range(1, 5)
        if position not in used_positions and position not in unresolved_positions
    ]
    if missing_positions:
        status = CheckStatus.FAILED
        explanation = f"No exact approved-form token was found for input positions {missing_positions}."
    elif unresolved_positions:
        status = CheckStatus.UNVERIFIED
        explanation = f"Input positions {unresolved_positions} are unresolved; mandatory-word use cannot be verified."
    else:
        status = CheckStatus.PASSED
        explanation = "All four input positions matched distinct exact approved-form token occurrences."
    return MandatoryWordValidation(
        status=status,
        required_words=required,
        used_words=used,
        missing_positions=missing_positions,
        unresolved_positions=unresolved_positions,
        explanation=explanation,
    )
