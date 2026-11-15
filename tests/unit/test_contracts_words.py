import pytest
from pydantic import ValidationError

from genkavya.contracts.common import ContractMetadata, VerificationStatus
from genkavya.contracts.words import (
    ApprovedWordForm, FourWordRequest, FourWordResolution, FormKind,
    FormVerification, GrammarFeatures, PartOfSpeech, SanskritWordRecord,
)


def form(status=VerificationStatus.VERIFIED, kind=FormKind.INFLECTION, relationship=None):
    return ApprovedWordForm(
        form_devanagari="रामेण", kind=kind, base_lemma_id="lemma-1", stem_id="stem-1",
        verification=FormVerification(status=status, source="grammar reference", source_reference="entry 1"),
        derivation_relationship=relationship,
    )


def record(position, word):
    return SanskritWordRecord(
        input_position=position, input_english=word, base_lemma_id="lemma-1",
        lemma_devanagari="राम", stem_id="stem-1", part_of_speech=PartOfSpeech.NOUN,
        grammar=GrammarFeatures(), approved_forms=[form()], meanings=[word],
        verification=FormVerification(status=VerificationStatus.VERIFIED, source="dictionary", source_reference="entry 1"),
    )


def test_duplicate_inputs_are_accepted_and_positions_preserved():
    request = FourWordRequest(english_words=("hero", "hero", "forest", "fire"))
    resolution = FourWordResolution(
        records=tuple(record(i, request.english_words[i - 1]) for i in range(1, 5)),
        metadata=ContractMetadata(producer="words"),
        lexicon_version="test",
    )
    assert [r.input_position for r in resolution.records] == [1, 2, 3, 4]
    assert resolution.records[0].input_english == resolution.records[1].input_english


def test_unverified_form_cannot_be_approved():
    with pytest.raises(ValidationError):
        form(status=VerificationStatus.UNVERIFIED)


def test_derivation_requires_documented_relationship():
    with pytest.raises(ValidationError):
        form(kind=FormKind.DERIVATION)

