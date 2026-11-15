"""Exact controlled-vocabulary lookup for four English input positions."""

from __future__ import annotations

from genkavya.contracts.words import FourWordRequest, FourWordResolution, WordResolutionStatus

from .adapters import entry_to_record, resolution_metadata, unresolved_record
from .lexicon import LexiconRepository, load_default_lexicon


def resolve_four_words(request: FourWordRequest, repository: LexiconRepository | None = None) -> FourWordResolution:
    """Resolve each position exactly; conflicts are ambiguous, never selected arbitrarily."""
    repository = repository or load_default_lexicon()
    records = []
    warnings: list[str] = []
    for position, english in enumerate(request.english_words, start=1):
        matches = repository.matches(english)
        lemma_ids = {entry["lemma"]["base_lemma_id"] for entry in matches}
        if len(lemma_ids) > 1:
            records.append(unresolved_record(english, position, WordResolutionStatus.AMBIGUOUS,
                f"The English lookup maps to conflicting Sanskrit lemmas: {', '.join(sorted(lemma_ids))}."))
            warnings.append(f"Input position {position} is ambiguous.")
        elif not matches:
            records.append(unresolved_record(english, position, WordResolutionStatus.UNRESOLVED,
                "No exact lookup exists in the controlled lexicon."))
            warnings.append(f"Input position {position} is unresolved.")
        else:
            record = entry_to_record(matches[0], english, position, repository)
            if record is None:
                records.append(unresolved_record(english, position, WordResolutionStatus.UNRESOLVED,
                    "A lexicon match exists, but its lemma or forms lack verified references."))
                warnings.append(f"Input position {position} has no eligible verified entry.")
            else:
                records.append(record)
    return FourWordResolution(
        records=tuple(records), warnings=warnings, metadata=resolution_metadata(), lexicon_version=repository.version,
    )
