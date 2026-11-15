"""Contracts for source-grounded Ramayana retrieval."""

from typing import Literal

from pydantic import AnyUrl, Field

from .common import ContractMetadata, ContractModel


class SceneRequest(ContractModel):
    scene_description: str = Field(min_length=1)
    top_k: int = Field(default=5, gt=0)


class SourceProvenance(ContractModel):
    source_id: str | None = None
    work: Literal["Valmiki Ramayana"] = "Valmiki Ramayana"
    translation: Literal["Manmatha Nath Dutt"] = "Manmatha Nath Dutt"
    kanda: Literal["Bāla Kāṇḍa", "Araṇya Kāṇḍa"]
    website_chapter: str | None = None
    part: int | None = Field(default=None, gt=0)
    section_id: str | None = None
    section_number: int | None = Field(default=None, gt=0)
    section_name: str | None = None
    source_url: AnyUrl | None = None
    source_file: str | None = None


class RetrievalScoreMetadata(ContractModel):
    metric: str = Field(min_length=1)
    embedding_normalized: bool
    interpretation: str = Field(min_length=1)


class RetrievedPassage(ContractModel):
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    provenance: SourceProvenance
    score: float | None = None
    score_metadata: RetrievalScoreMetadata | None = None
    rank: int = Field(gt=0)
    retrieval_role: Literal["primary", "adjacent_context"] = "primary"


class RagEvidence(ContractModel):
    status: Literal["success", "insufficient_evidence"]
    query: SceneRequest
    passages: list[RetrievedPassage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: ContractMetadata

