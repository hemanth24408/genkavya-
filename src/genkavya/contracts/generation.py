"""Contracts for generating five four-pāda candidates."""

from enum import StrEnum
from pydantic import Field, model_validator

from .common import ContractMetadata, ContractModel, VerificationStatus
from .rag import RagEvidence, SceneRequest
from .words import FourWordResolution, WordResolutionStatus


class MeterName(StrEnum):
    CLASSICAL_ANUSTUBH = "classical_anustubh"


class GenerationRequest(ContractModel):
    scene: SceneRequest
    evidence: RagEvidence
    words: FourWordResolution
    candidate_count: int = Field(default=5, frozen=True)
    meter: MeterName = MeterName.CLASSICAL_ANUSTUBH

    @model_validator(mode="after")
    def require_five_candidates(self):
        if self.candidate_count != 5:
            raise ValueError("Exactly five candidates are required")
        if len(self.words.records) != 4 or any(
            record.resolution_status != WordResolutionStatus.EXACT
            or record.verification is None
            or record.verification.status != VerificationStatus.VERIFIED
            or not record.approved_forms
            or any(form.verification.status != VerificationStatus.VERIFIED for form in record.approved_forms)
            for record in self.words.records
        ):
            raise ValueError("Generation requires four resolved words with verified lemmas and approved forms")
        return self


class SanskritCandidate(ContractModel):
    candidate_id: str = Field(min_length=1)
    padas: tuple[str, str, str, str]
    english_summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_nonempty_padas(self):
        if any(not pada.strip() for pada in self.padas):
            raise ValueError("All four padas must contain text")
        multiline_positions = [
            position for position, pada in enumerate(self.padas, start=1)
            if "\n" in pada or "\r" in pada
        ]
        if multiline_positions:
            positions = ", ".join(str(position) for position in multiline_positions)
            raise ValueError(
                f"Each pada must be a single line; embedded newline or carriage return in pada position(s): {positions}"
            )
        return self


SANSKRIT_CANDIDATE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "padas": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "pattern": "^[^\\r\\n]+$",
            },
            "minItems": 4,
            "maxItems": 4,
        },
        "english_summary": {"type": "string", "minLength": 1},
    },
    "required": ["padas", "english_summary"],
    "additionalProperties": False,
}


class GenerationResponse(ContractModel):
    candidates: tuple[
        SanskritCandidate, SanskritCandidate, SanskritCandidate,
        SanskritCandidate, SanskritCandidate,
    ]
    metadata: ContractMetadata

    @model_validator(mode="after")
    def require_unique_candidate_ids(self):
        if len({candidate.candidate_id for candidate in self.candidates}) != 5:
            raise ValueError("The five candidate IDs must be unique")
        return self

