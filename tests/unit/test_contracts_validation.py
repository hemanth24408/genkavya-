import pytest
from pydantic import ValidationError

from genkavya.contracts.common import CheckStatus, ContractMetadata
from genkavya.contracts.generation import MeterName, SanskritCandidate
from genkavya.contracts.validation import (
    CandidateValidation, GrammarStatus, MandatoryWordValidation, MeterCheckName,
    MeterRuleResult, MeterValidation, UsedWord, ValidationResponse,
)


def candidate(i, padas=None):
    return SanskritCandidate(
        candidate_id=f"c{i}", padas=padas or (f"a{i}", f"b{i}", f"c{i}", f"d{i}"), english_summary="summary"
    )


def item(i, grammar=GrammarStatus.UNVERIFIED, meter=CheckStatus.PASSED, words=CheckStatus.PASSED,
         duplicate=False):
    used = [UsedWord(
        input_position=position, input_english=word, matched_form_devanagari="वन",
        base_lemma_id=f"lemma-{position}", stem_id=f"stem-{position}",
        form_kind="inflection", pada_numbers=[1], token_index=position - 1,
    ) for position, word in enumerate(("a", "b", "c", "d"), 1)]
    meter_checks = tuple(MeterRuleResult(
        check=name, status=meter, explanation="passed" if meter == CheckStatus.PASSED else "not passed",
    ) for name in (MeterCheckName.PADA_STRUCTURE, MeterCheckName.SYLLABLE_COUNT, MeterCheckName.LAGHU_GURU_PATTERN))
    mandatory = MandatoryWordValidation(
        status=words, required_words=("a", "b", "c", "d"), used_words=used if words == CheckStatus.PASSED else [],
        missing_positions=[] if words == CheckStatus.PASSED else [1, 2, 3, 4],
        explanation="passed" if words == CheckStatus.PASSED else "approved forms were not found",
    )
    grammar_explanation = None
    tags = []
    if grammar == GrammarStatus.UNVERIFIED:
        grammar_explanation, tags = "Grammar could not be verified.", ["grammar_unverified"]
    elif grammar == GrammarStatus.ISSUES_FOUND:
        grammar_explanation, tags = "A specific grammar issue was identified.", ["grammar_issues_found"]
    return CandidateValidation(
        candidate=candidate(i),
        meter=MeterValidation(
            status=meter, meter=MeterName.CLASSICAL_ANUSTUBH, pada_count=4,
            syllable_counts=[8, 8, 8, 8], laghu_guru_patterns=["LGGLGGGG"] * 4,
            checks=meter_checks, method="test",
        ),
        mandatory_words=mandatory, grammar_status=grammar,
        grammar_explanation=grammar_explanation, grammar_warning_tags=tags,
        duplicate_candidate=duplicate,
    )


def test_validation_response_contains_five_results_without_overall_groups():
    results = tuple(item(i) for i in range(5))
    response = ValidationResponse(candidates=results, metadata=ContractMetadata(producer="validator"))
    assert len(response.candidates) == 5
    assert not hasattr(response, "valid_candidates")
    assert not hasattr(response, "invalid_candidates")


@pytest.mark.parametrize("grammar", list(GrammarStatus))
def test_grammar_status_is_independent_of_word_and_meter_results(grammar):
    results = [item(i) for i in range(5)]
    results[0] = item(0, grammar=grammar, meter=CheckStatus.FAILED, words=CheckStatus.FAILED)
    response = ValidationResponse(candidates=tuple(results), metadata=ContractMetadata(producer="validator"))
    assert response.candidates[0].grammar_status == grammar
    assert response.candidates[0].meter.status == CheckStatus.FAILED
    assert response.candidates[0].mandatory_words.status == CheckStatus.FAILED


@pytest.mark.parametrize("count", [4, 6])
def test_validation_contract_rejects_non_five_candidate_count(count):
    with pytest.raises(ValidationError):
        ValidationResponse(
            candidates=tuple(item(i) for i in range(count)),
            metadata=ContractMetadata(producer="validator"),
        )


def test_duplicate_poems_remain_in_evaluation_and_can_be_flagged():
    duplicate_results = [item(i) for i in range(5)]
    duplicate_results[1] = item(1, duplicate=True)
    duplicate_results[0].candidate = candidate(0, ("same", "same", "same", "same"))
    duplicate_results[1].candidate = candidate(1, ("same", "same", "same", "same"))
    response = ValidationResponse(candidates=tuple(duplicate_results), metadata=ContractMetadata(producer="validator"))
    assert len(response.candidates) == 5
    assert response.candidates[1].duplicate_candidate is True


def test_one_token_occurrence_cannot_satisfy_two_positions():
    duplicate_occurrence = item(0).mandatory_words.model_copy(update={
        "used_words": [item(0).mandatory_words.used_words[0]] * 4,
    })
    with pytest.raises(ValidationError):
        duplicate_occurrence.model_validate(duplicate_occurrence.model_dump())
