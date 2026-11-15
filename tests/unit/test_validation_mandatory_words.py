from genkavya.contracts.common import ContractMetadata, VerificationStatus
from genkavya.contracts.generation import SanskritCandidate
from genkavya.contracts.words import (
    ApprovedWordForm, FormKind, FormVerification, FourWordResolution, PartOfSpeech,
    SanskritWordRecord, WordResolutionStatus,
)
from genkavya.validation.mandatory_words import validate_mandatory_words


def resolution(words):
    records = []
    for position, word in enumerate(words, 1):
        lemma = f"lemma-{position}"
        records.append(SanskritWordRecord(
            input_position=position, input_english=word, resolution_status=WordResolutionStatus.EXACT,
            base_lemma_id=lemma, lemma_devanagari="वन", stem_id=f"stem-{position}",
            part_of_speech=PartOfSpeech.NOUN,
            verification=FormVerification(status=VerificationStatus.VERIFIED, source="fixture", source_reference="test-fixture"),
            approved_forms=[ApprovedWordForm(
                form_devanagari=f"व{position}", kind=FormKind.INFLECTION,
                base_lemma_id=lemma, stem_id=f"stem-{position}",
                verification=FormVerification(status=VerificationStatus.VERIFIED, source="fixture", source_reference="test-fixture"),
            )],
        ))
    return FourWordResolution(
        records=tuple(records), metadata=ContractMetadata(producer="test"), lexicon_version="fixture",
    )


def candidate(padas):
    return SanskritCandidate(candidate_id="c", padas=tuple(padas), english_summary="fixture")


def test_exact_forms_can_appear_in_any_pada_and_share_a_pada():
    result = validate_mandatory_words(candidate(("व1 व2", "क्ष", "व3", "व4")), resolution(("a", "b", "c", "d")))
    assert result.status.value == "passed"
    assert [item.pada_numbers[0] for item in result.used_words] == [1, 1, 3, 4]


def test_duplicate_input_positions_need_distinct_token_occurrences():
    words = resolution(("a", "a", "c", "d"))
    words.records[1].approved_forms[0].form_devanagari = words.records[0].approved_forms[0].form_devanagari
    result = validate_mandatory_words(candidate(("व1", "व3", "व4", "क्ष")), words)
    assert result.status.value == "failed"
    assert result.missing_positions == [2]


def test_duplicate_inputs_pass_with_two_occurrences():
    words = resolution(("a", "a", "c", "d"))
    words.records[1].approved_forms[0].form_devanagari = words.records[0].approved_forms[0].form_devanagari
    result = validate_mandatory_words(candidate(("व1 व1", "व3", "व4", "क्ष")), words)
    assert result.status.value == "passed"
    assert len({(item.pada_numbers[0], item.token_index) for item in result.used_words}) == 4


def test_unresolved_input_is_unverified_and_explained():
    words = resolution(("a", "b", "c", "d"))
    records = list(words.records)
    records[2] = SanskritWordRecord(
        input_position=3, input_english="c", resolution_status=WordResolutionStatus.UNRESOLVED,
        resolution_explanation="No lexicon entry.",
    )
    words.records = tuple(records)
    result = validate_mandatory_words(candidate(("व1", "व2", "व4", "क्ष")), words)
    assert result.status.value == "unverified"
    assert result.unresolved_positions == [3]
