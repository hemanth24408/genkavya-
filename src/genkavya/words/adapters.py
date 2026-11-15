"""Adapters from verified JSON lexicon records to Phase 1 word contracts."""

from __future__ import annotations

from typing import Any

from genkavya.contracts.common import ContractMetadata, VerificationStatus
from genkavya.contracts.words import (
    ApprovedWordForm, DerivationRelationship, FormKind, FormVerification,
    GrammarFeatures, PartOfSpeech, SanskritWordRecord, WordResolutionStatus,
)

from .lexicon import LexiconRepository


def _verification(raw: dict[str, Any], repository: LexiconRepository) -> FormVerification:
    refs = raw.get("reference_ids", [])
    return FormVerification(
        status=VerificationStatus(raw["status"]),
        source="; ".join(repository.references[ref]["title"] + " (" + repository.references[ref]["edition"] + ")" for ref in refs) or "Unverified lexicon record",
        source_reference=repository.reference_text(refs),
        reviewer=raw.get("reviewer"),
    )


def _grammar(raw: dict[str, Any] | None) -> GrammarFeatures:
    raw = raw or {}
    known = {k: raw.get(k) for k in ("case", "number", "gender", "person", "tense_mood", "voice")}
    known["additional"] = raw.get("additional", {})
    return GrammarFeatures(**known)


def entry_to_record(entry: dict[str, Any], english: str, position: int, repository: LexiconRepository) -> SanskritWordRecord | None:
    """Adapt one entry; return None unless lemma and at least one form are verified."""
    lemma = entry["lemma"]
    lemma_ver = lemma["verification"]
    if lemma_ver["status"] != VerificationStatus.VERIFIED.value:
        return None
    lemma_reference = repository.reference_text(lemma_ver["reference_ids"])
    if not lemma_reference:
        return None
    forms = [ApprovedWordForm(
        form_devanagari=lemma["devanagari"], iast=lemma.get("iast"), kind=FormKind.LEMMA,
        base_lemma_id=lemma["base_lemma_id"], stem_id=lemma["stem_id"],
        grammar=_grammar(lemma.get("grammar")), verification=_verification(lemma_ver, repository),
    )]
    for kind, values in ((FormKind.INFLECTION, entry["inflections"]), (FormKind.DERIVATION, entry["derivations"])):
        for raw in values:
            if raw["verification"]["status"] != VerificationStatus.VERIFIED.value:
                continue
            relationship = None
            if kind == FormKind.DERIVATION:
                rel = raw["derivation_relationship"]
                rel_ref = repository.reference_text([rel.get("source_reference_id", "")])
                if not rel_ref:
                    continue
                relationship = DerivationRelationship(
                    relationship_type=rel["relationship_type"], description=rel["description"],
                    source=rel.get("rule_reference", rel_ref), source_reference=rel_ref,
                )
            forms.append(ApprovedWordForm(
                form_devanagari=raw["devanagari"], iast=raw.get("iast"), kind=kind,
                base_lemma_id=raw["base_lemma_id"], stem_id=raw["stem_id"],
                grammar=_grammar(raw.get("grammar")), derivation_relationship=relationship,
                verification=_verification(raw["verification"], repository),
            ))
    return SanskritWordRecord(
        input_position=position, input_english=english, resolution_status=WordResolutionStatus.EXACT,
        base_lemma_id=lemma["base_lemma_id"], lemma_devanagari=lemma["devanagari"],
        lemma_iast=lemma.get("iast"), stem_id=lemma["stem_id"],
        part_of_speech=PartOfSpeech(lemma["part_of_speech"]), grammar=_grammar(lemma.get("grammar")),
        approved_forms=forms, meanings=list(entry["english_meanings"]), verification=_verification(lemma_ver, repository),
    ) if forms else None


def unresolved_record(english: str, position: int, status: WordResolutionStatus, explanation: str) -> SanskritWordRecord:
    return SanskritWordRecord(
        input_position=position, input_english=english, resolution_status=status,
        resolution_explanation=explanation,
    )


def resolution_metadata() -> ContractMetadata:
    return ContractMetadata(producer="genkavya.words")
