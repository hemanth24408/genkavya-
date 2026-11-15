from genkavya.contracts.words import FourWordRequest, FormKind, WordResolutionStatus
from genkavya.words.lexicon import LexiconRepository
from genkavya.words.resolver import resolve_four_words
from test_word_lexicon import fixture_document


def test_adapter_emits_only_verified_forms_with_citations():
    result = resolve_four_words(FourWordRequest(english_words=("test term",) * 4), LexiconRepository(fixture_document()))
    first = result.records[0]
    assert first.resolution_status == WordResolutionStatus.EXACT
    assert {form.kind for form in first.approved_forms} == {FormKind.LEMMA, FormKind.INFLECTION}
    assert all(form.verification.status.value == "verified" for form in first.approved_forms)
    assert all(form.verification.source_reference for form in first.approved_forms)
    assert all(form.base_lemma_id == first.base_lemma_id and form.stem_id == first.stem_id for form in first.approved_forms)


def test_unverified_forms_are_filtered_out():
    document = fixture_document()
    document["entries"][0]["inflections"][0]["verification"]["status"] = "unverified"
    result = resolve_four_words(FourWordRequest(english_words=("test term",) * 4), LexiconRepository(document))
    assert len(result.records[0].approved_forms) == 1
    assert result.records[0].approved_forms[0].kind == FormKind.LEMMA
