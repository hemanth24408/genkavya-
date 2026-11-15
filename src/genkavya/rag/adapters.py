"""Adapters between legacy retrieval dictionaries and Phase 1 contracts."""

from typing import Any

from genkavya.contracts.common import ContractMetadata
from genkavya.contracts.rag import RagEvidence, RetrievedPassage, SceneRequest, SourceProvenance

from . import config


def passage_to_contract(passage: dict[str, Any], *, rank: int, role: str = "primary") -> RetrievedPassage:
    kanda = passage.get("kanda")
    if kanda not in config.KANDA_CONTRACT_LABELS:
        raise ValueError(f"Cannot adapt passage with out-of-scope Kanda: {kanda!r}.")
    return RetrievedPassage(
        chunk_id=passage["chunk_id"],
        text=passage["text"],
        rank=rank,
        score=passage.get("similarity_score"),
        score_metadata=config.score_metadata() if passage.get("similarity_score") is not None else None,
        retrieval_role=role,
        provenance=SourceProvenance(
            source_id=passage["source_id"],
            work="Valmiki Ramayana",
            translation=passage["translator"],
            kanda=config.KANDA_CONTRACT_LABELS[kanda],
            website_chapter=passage["website_chapter"],
            part=passage["part"],
            section_id=passage["section_id"],
            section_number=passage["section_number"],
            section_name=passage["section_name"],
            source_url=passage["source_url"],
            source_file=passage["source_file"],
        ),
    )


def legacy_evidence_to_contract(evidence: dict[str, Any]) -> RagEvidence:
    """Convert the old evidence dictionary without filling absent provenance."""
    status = evidence.get("status")
    if status == "retrieval_error":
        raise RuntimeError(str(evidence.get("error") or "Ramayana retrieval failed."))
    if status not in {"success", "insufficient_evidence"}:
        raise ValueError(f"Unsupported legacy evidence status: {status!r}.")

    passages = []
    primary_rank = 0
    adjacent_rank = 0
    for item in evidence.get("evidence_passages", []):
        role = item.get("retrieval_role", "primary")
        if role == "adjacent_context":
            adjacent_rank += 1
            rank = adjacent_rank
        else:
            primary_rank += 1
            rank = item.get("combined_rank") or item.get("rank") or primary_rank
        passages.append(passage_to_contract(item, rank=rank, role=role))

    warnings = []
    if status == "insufficient_evidence":
        warnings.append("No primary passages were retrieved; evidence is insufficient.")
    return RagEvidence(
        status=status,
        query=SceneRequest(scene_description=evidence["user_situation"]),
        passages=passages,
        warnings=warnings,
        metadata=ContractMetadata(producer="genkavya.rag"),
    )

