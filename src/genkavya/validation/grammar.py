"""Conservative sentence-grammar result; lexical evidence is not grammar proof."""

from genkavya.contracts.generation import SanskritCandidate
from genkavya.contracts.validation import GrammarStatus


def validate_grammar(candidate: SanskritCandidate) -> tuple[GrammarStatus, str, list[str]]:
    """Return unverified until a reliable sentence-level Sanskrit validator is configured."""
    return (
        GrammarStatus.UNVERIFIED,
        "Sentence-level Sanskrit grammar could not be verified by the configured system.",
        ["grammar_unverified"],
    )
