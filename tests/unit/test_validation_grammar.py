from genkavya.contracts.generation import SanskritCandidate
from genkavya.contracts.validation import GrammarStatus
from genkavya.validation.grammar import validate_grammar


def test_grammar_is_unverified_without_sentence_level_checker():
    candidate = SanskritCandidate(candidate_id="c", padas=("a", "b", "c", "d"), english_summary="summary")
    status, explanation, tags = validate_grammar(candidate)
    assert status == GrammarStatus.UNVERIFIED
    assert "could not be verified" in explanation
    assert tags == ["grammar_unverified"]
