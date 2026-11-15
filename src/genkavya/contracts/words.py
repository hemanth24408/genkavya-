"""Contracts for four-position English-to-Sanskrit word resolution."""

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .common import ContractMetadata, ContractModel, VerificationStatus


class PartOfSpeech(StrEnum):
    NOUN = "noun"
    ADJECTIVE = "adjective"
    VERB = "verb"
    INDECLINABLE = "indeclinable"
    OTHER = "other"


class FormKind(StrEnum):
    LEMMA = "lemma"
    INFLECTION = "inflection"
    DERIVATION = "derivation"


class WordResolutionStatus(StrEnum):
    EXACT = "exact"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class GrammarFeatures(ContractModel):
    case: str | None = None
    number: str | None = None
    gender: str | None = None
    person: str | None = None
    tense_mood: str | None = None
    voice: str | None = None
    additional: dict[str, str] = Field(default_factory=dict)


class FormVerification(ContractModel):
    status: VerificationStatus
    source: str = Field(min_length=1)
    source_reference: str | None = None
    reviewer: str | None = None

    @model_validator(mode="after")
    def verified_needs_reference(self):
        if self.status == VerificationStatus.VERIFIED and not (self.source_reference or "").strip():
            raise ValueError("Verified words and forms require a traceable source reference")
        return self


class DerivationRelationship(ContractModel):
    relationship_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_reference: str | None = None


class ApprovedWordForm(ContractModel):
    form_devanagari: str = Field(min_length=1)
    iast: str | None = None
    kind: FormKind
    base_lemma_id: str = Field(min_length=1)
    stem_id: str = Field(min_length=1)
    grammar: GrammarFeatures = Field(default_factory=GrammarFeatures)
    derivation_relationship: DerivationRelationship | None = None
    verification: FormVerification

    @model_validator(mode="after")
    def check_relationship_metadata(self):
        if self.verification.status != VerificationStatus.VERIFIED:
            raise ValueError("Only verified forms may be listed as approved forms")
        if self.kind == FormKind.DERIVATION and self.derivation_relationship is None:
            raise ValueError("A derivational form requires relationship metadata")
        return self


class SanskritWordRecord(ContractModel):
    input_position: Literal[1, 2, 3, 4]
    input_english: str = Field(min_length=1)
    resolution_status: WordResolutionStatus = WordResolutionStatus.EXACT
    resolution_explanation: str | None = None
    base_lemma_id: str | None = None
    lemma_devanagari: str | None = None
    lemma_iast: str | None = None
    stem_id: str | None = None
    part_of_speech: PartOfSpeech | None = None
    grammar: GrammarFeatures = Field(default_factory=GrammarFeatures)
    approved_forms: list[ApprovedWordForm] = Field(default_factory=list)
    meanings: list[str] = Field(default_factory=list)
    verification: FormVerification | None = None

    @model_validator(mode="after")
    def check_form_bases(self):
        if self.resolution_status == WordResolutionStatus.EXACT:
            if not all((self.base_lemma_id, self.lemma_devanagari, self.stem_id, self.part_of_speech)):
                raise ValueError("Exact resolutions require lemma, stem, and part-of-speech identity")
            if self.verification is None or self.verification.status != VerificationStatus.VERIFIED:
                raise ValueError("Exact resolutions require a verified lemma")
            if not self.approved_forms:
                raise ValueError("Exact resolutions require at least one approved form")
        else:
            if self.approved_forms:
                raise ValueError("Ambiguous or unresolved results cannot contain approved forms")
        for form in self.approved_forms:
            if form.base_lemma_id != self.base_lemma_id:
                raise ValueError("Approved form base_lemma_id must match its word record")
            if form.stem_id != self.stem_id:
                raise ValueError("Approved form stem_id must match its word record")
        return self


class FourWordRequest(ContractModel):
    english_words: tuple[str, str, str, str]

    @model_validator(mode="after")
    def require_four_nonempty_positions(self):
        if any(not word.strip() for word in self.english_words):
            raise ValueError("All four English input positions must contain a word")
        return self


class FourWordResolution(ContractModel):
    records: tuple[SanskritWordRecord, SanskritWordRecord, SanskritWordRecord, SanskritWordRecord]
    warnings: list[str] = Field(default_factory=list)
    metadata: ContractMetadata
    lexicon_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def preserve_input_positions(self):
        for position, record in enumerate(self.records, 1):
            if record.input_position != position:
                raise ValueError("Word records must preserve input position order")
        return self

