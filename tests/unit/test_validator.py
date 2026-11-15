from genkavya.contracts.common import ContractMetadata, VerificationStatus
from genkavya.contracts.generation import GenerationResponse, SanskritCandidate
from genkavya.contracts.words import (
    ApprovedWordForm, FormKind, FormVerification, FourWordResolution, PartOfSpeech,
    SanskritWordRecord, WordResolutionStatus,
)
from genkavya.contracts.validation import ValidationRequest
from genkavya.validation import validate


def request():
    records = []
    for position in range(1, 5):
        lemma = f"lemma-{position}"
        ref = FormVerification(status=VerificationStatus.VERIFIED, source="test", source_reference="fixture")
        records.append(SanskritWordRecord(
            input_position=position, input_english=f"word-{position}", resolution_status=WordResolutionStatus.EXACT,
            base_lemma_id=lemma, lemma_devanagari="वन", stem_id=f"stem-{position}",
            part_of_speech=PartOfSpeech.NOUN, verification=ref,
            approved_forms=[ApprovedWordForm(form_devanagari=f"w{position}", kind=FormKind.LEMMA,
                base_lemma_id=lemma, stem_id=f"stem-{position}", verification=ref)],
        ))
    words = FourWordResolution(records=tuple(records), metadata=ContractMetadata(producer="test"), lexicon_version="fixture")
    candidates = tuple(SanskritCandidate(
        candidate_id=f"c{i}", padas=(f"w1 w2 w3 w4 {i}", f"p2-{i}", f"p3-{i}", f"p4-{i}"),
        english_summary="summary",
    ) for i in range(5))
    generation = GenerationResponse(candidates=candidates, metadata=ContractMetadata(producer="test"))
    return ValidationRequest(generation=generation, words=words)


def test_all_five_candidates_receive_independent_results(monkeypatch):
    from genkavya.contracts.common import CheckStatus
    from genkavya.contracts.validation import MeterCheckName, MeterRuleResult, MeterValidation
    from genkavya.contracts.generation import MeterName

    calls = {"meter": 0}

    def passed_meter(candidate):
        calls["meter"] += 1
        checks = tuple(MeterRuleResult(check=name, status=CheckStatus.PASSED, explanation="pass") for name in MeterCheckName)
        return MeterValidation(status=CheckStatus.PASSED, meter=MeterName.CLASSICAL_ANUSTUBH,
            pada_count=4, syllable_counts=[8] * 4, laghu_guru_patterns=["LGGLGGGG"] * 4,
            checks=checks, method="mock")

    monkeypatch.setattr("genkavya.validation.validator.validate_meter", passed_meter)
    response = validate(request())
    assert len(response.candidates) == 5
    assert len({item.candidate.candidate_id for item in response.candidates}) == 5
    assert all(item.grammar_status.value == "unverified" for item in response.candidates)
    assert calls["meter"] == 5


def test_unverified_meter_reason_is_not_reported_as_confirmed_failure(monkeypatch):
    from genkavya.contracts.common import CheckStatus
    from genkavya.contracts.validation import MeterCheckName, MeterRuleResult, MeterValidation
    from genkavya.contracts.generation import MeterName

    def unverified_meter(candidate):
        checks = tuple(MeterRuleResult(check=name, status=CheckStatus.UNVERIFIED, explanation="backend unavailable") for name in MeterCheckName)
        return MeterValidation(status=CheckStatus.UNVERIFIED, meter=MeterName.CLASSICAL_ANUSTUBH,
            pada_count=4, syllable_counts=[None] * 4, laghu_guru_patterns=[None] * 4,
            checks=checks, method="mock", explanation="Chanda unavailable")

    monkeypatch.setattr("genkavya.validation.validator.validate_meter", unverified_meter)
    response = validate(request())
    assert len(response.candidates) == 5
    assert all(item.meter.status == CheckStatus.UNVERIFIED for item in response.candidates)
    assert all("Meter check unverified:" in item.invalid_reasons[0] for item in response.candidates)


def test_duplicates_are_evaluated_and_marked_without_discarding(monkeypatch):
    from genkavya.contracts.generation import GenerationResponse

    req = request()
    repeated = req.generation.candidates[0].model_copy(update={
        "candidate_id": "duplicate", "padas": req.generation.candidates[0].padas,
    })
    generation = GenerationResponse(
        candidates=(req.generation.candidates[0], repeated, *req.generation.candidates[2:]),
        metadata=req.generation.metadata,
    )
    req = req.model_copy(update={"generation": generation})
    monkeypatch.setattr("genkavya.validation.validator.validate_meter", lambda candidate: _passed_meter())
    response = validate(req)
    assert len(response.candidates) == 5
    assert [item.duplicate_candidate for item in response.candidates[:2]] == [False, True]


def test_missing_words_and_meter_failures_still_return_all_five_evaluations(monkeypatch):
    from genkavya.contracts.common import CheckStatus
    from genkavya.contracts.generation import GenerationResponse

    req = request()
    poems = tuple(req.generation.candidates)
    no_words = tuple(poem.model_copy(update={
        "padas": (f"unmatched verse {i}", "line two", "line three", "line four"),
    }) for i, poem in enumerate(poems))
    req = req.model_copy(update={"generation": GenerationResponse(
        candidates=no_words, metadata=req.generation.metadata,
    )})
    monkeypatch.setattr("genkavya.validation.validator.validate_meter", lambda candidate: _failed_meter())

    response = validate(req)
    assert len(response.candidates) == 5
    assert all(result.mandatory_words.status == CheckStatus.FAILED for result in response.candidates)
    assert all(result.mandatory_words.missing_positions == [1, 2, 3, 4] for result in response.candidates)
    assert all(result.meter.status == CheckStatus.FAILED for result in response.candidates)
    assert all(result.meter.checks[1].explanation == "10 syllables; expected exactly 8." for result in response.candidates)


def _passed_meter():
    from genkavya.contracts.common import CheckStatus
    from genkavya.contracts.validation import MeterCheckName, MeterRuleResult, MeterValidation
    from genkavya.contracts.generation import MeterName
    checks = tuple(MeterRuleResult(check=name, status=CheckStatus.PASSED, explanation="pass") for name in MeterCheckName)
    return MeterValidation(status=CheckStatus.PASSED, meter=MeterName.CLASSICAL_ANUSTUBH,
        pada_count=4, syllable_counts=[8] * 4, laghu_guru_patterns=["LGGLGGGG"] * 4,
        checks=checks, method="mock")


def _failed_meter():
    from genkavya.contracts.common import CheckStatus
    from genkavya.contracts.validation import MeterCheckName, MeterRuleResult, MeterValidation
    from genkavya.contracts.generation import MeterName
    explanations = ("Four padas were found.", "10 syllables; expected exactly 8.", "Required cadence does not match.")
    checks = tuple(MeterRuleResult(check=name, status=CheckStatus.FAILED, explanation=explanation)
                   for name, explanation in zip(MeterCheckName, explanations))
    return MeterValidation(status=CheckStatus.FAILED, meter=MeterName.CLASSICAL_ANUSTUBH,
        pada_count=4, syllable_counts=[10] * 4, laghu_guru_patterns=["LLLLLLLLLL"] * 4,
        checks=checks, method="mock", explanation="Meter checks failed")
