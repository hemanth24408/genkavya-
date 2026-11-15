"""Independent candidate checks and exclusive valid/invalid classification."""

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .common import ContractMetadata, ContractModel, CheckStatus
from .generation import GenerationResponse, MeterName, SanskritCandidate
from .words import FormKind, FourWordResolution


class GrammarStatus(StrEnum):
    VERIFIED = "verified"
    ISSUES_FOUND = "issues_found"
    UNVERIFIED = "unverified"


class MeterCheckName(StrEnum):
    PADA_STRUCTURE = "pada_structure"
    SYLLABLE_COUNT = "syllable_count"
    LAGHU_GURU_PATTERN = "laghu_guru_pattern"


class MeterRuleResult(ContractModel):
    check: MeterCheckName
    status: CheckStatus
    explanation: str


class MeterValidation(ContractModel):
    status: CheckStatus
    meter: MeterName
    pada_count: int = Field(ge=0)
    syllable_counts: list[int | None] = Field(min_length=4, max_length=4)
    laghu_guru_patterns: list[str | None] = Field(min_length=4, max_length=4)
    checks: tuple[MeterRuleResult, MeterRuleResult, MeterRuleResult]
    explanation: str | None = None
    method: str = Field(min_length=1)

    @model_validator(mode="after")
    def aggregate_check_status(self):
        statuses = {check.status for check in self.checks}
        expected = CheckStatus.FAILED if CheckStatus.FAILED in statuses else (
            CheckStatus.UNVERIFIED if CheckStatus.UNVERIFIED in statuses else CheckStatus.PASSED
        )
        if self.status != expected:
            raise ValueError("Overall meter status must reflect the three independent check results")
        return self


class UsedWord(ContractModel):
    input_position: Literal[1, 2, 3, 4]
    input_english: str = Field(min_length=1)
    matched_form_devanagari: str = Field(min_length=1)
    base_lemma_id: str = Field(min_length=1)
    stem_id: str = Field(min_length=1)
    form_kind: FormKind
    pada_numbers: list[Literal[1, 2, 3, 4]] = Field(min_length=1)
    token_index: int = Field(ge=0)
    form_verification: Literal["verified"] = "verified"


class MandatoryWordValidation(ContractModel):
    status: CheckStatus
    required_words: tuple[str, str, str, str]
    used_words: list[UsedWord] = Field(default_factory=list)
    missing_positions: list[Literal[1, 2, 3, 4]] = Field(default_factory=list)
    unresolved_positions: list[Literal[1, 2, 3, 4]] = Field(default_factory=list)
    explanation: str | None = None

    @model_validator(mode="after")
    def check_position_accounting(self):
        present = {word.input_position for word in self.used_words}
        missing = set(self.missing_positions)
        unresolved = set(self.unresolved_positions)
        if any(word.input_english != self.required_words[word.input_position - 1] for word in self.used_words):
            raise ValueError("Used-word English input must match its original position")
        if len(present) != len(self.used_words):
            raise ValueError("Each input position may be represented by only one used-word record")
        if present & (missing | unresolved) or missing & unresolved:
            raise ValueError("A position cannot be used, missing, or unresolved more than once")
        occurrences = [(word.pada_numbers[0], word.token_index) for word in self.used_words if len(word.pada_numbers) == 1]
        if len(occurrences) != len(self.used_words) or len(set(occurrences)) != len(occurrences):
            raise ValueError("Each used-word record must identify a unique token occurrence in one pada")
        if (present | missing | unresolved) != {1, 2, 3, 4}:
            raise ValueError("Mandatory-word check must account for all four positions")
        if self.status == CheckStatus.PASSED and (missing or unresolved or present != {1, 2, 3, 4}):
            raise ValueError("Passed mandatory-word check must match all four positions")
        return self


class CandidateValidation(ContractModel):
    candidate: SanskritCandidate
    meter: MeterValidation
    mandatory_words: MandatoryWordValidation
    grammar_status: GrammarStatus
    grammar_explanation: str | None = None
    grammar_warning_tags: list[str] = Field(default_factory=list)
    rank: int | None = Field(default=None, gt=0)
    score: float | None = None
    duplicate_candidate: bool = False
    invalid_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_grammar_explanation_when_needed(self):
        if self.grammar_status in (GrammarStatus.UNVERIFIED, GrammarStatus.ISSUES_FOUND) and not (self.grammar_explanation or "").strip():
            raise ValueError("Unverified or issue-bearing grammar requires an explanation")
        if self.grammar_status == GrammarStatus.ISSUES_FOUND and "grammar_issues_found" not in self.grammar_warning_tags:
            raise ValueError("Grammar issues require a visible warning tag")
        if self.grammar_status == GrammarStatus.UNVERIFIED and "grammar_unverified" not in self.grammar_warning_tags:
            raise ValueError("Unverified grammar requires a visible warning tag")
        return self


class ValidationRequest(ContractModel):
    generation: GenerationResponse
    words: FourWordResolution


class ValidationResponse(ContractModel):
    candidates: tuple[
        CandidateValidation, CandidateValidation, CandidateValidation,
        CandidateValidation, CandidateValidation,
    ]
    metadata: ContractMetadata

    @model_validator(mode="after")
    def account_for_five_candidates(self):
        ids = [item.candidate.candidate_id for item in self.candidates]
        if len(set(ids)) != 5:
            raise ValueError("Evaluation must account for five candidates with unique IDs")
        return self

