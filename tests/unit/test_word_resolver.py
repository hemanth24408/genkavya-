from copy import deepcopy

from genkavya.contracts.words import FourWordRequest, WordResolutionStatus
from genkavya.words.lexicon import LexiconRepository
from genkavya.words.resolver import resolve_four_words
from test_word_lexicon import fixture_document


def test_four_positions_and_duplicate_inputs_are_preserved():
    result = resolve_four_words(FourWordRequest(english_words=("test term", "test term", "missing", "test term")),
                                LexiconRepository(fixture_document()))
    assert len(result.records) == 4
    assert [record.input_position for record in result.records] == [1, 2, 3, 4]
    assert result.records[0].input_english == result.records[1].input_english
    assert result.records[2].resolution_status == WordResolutionStatus.UNRESOLVED


def test_conflicting_lemma_mappings_are_ambiguous():
    document = fixture_document()
    conflict = deepcopy(document["entries"][0])
    conflict["word_id"] = "second-test-word"
    conflict["lemma"]["base_lemma_id"] = "other-lemma"
    conflict["lemma"]["stem_id"] = "other-stem"
    conflict["inflections"][0]["base_lemma_id"] = "other-lemma"
    conflict["inflections"][0]["stem_id"] = "other-stem"
    document["entries"].append(conflict)
    result = resolve_four_words(FourWordRequest(english_words=("test term",) * 4), LexiconRepository(document))
    assert all(record.resolution_status == WordResolutionStatus.AMBIGUOUS for record in result.records)
    assert all(not record.approved_forms for record in result.records)


def test_unverified_match_never_becomes_generation_eligible():
    document = fixture_document()
    document["entries"][0]["lemma"]["verification"]["status"] = "unverified"
    result = resolve_four_words(FourWordRequest(english_words=("test term",) * 4), LexiconRepository(document))
    assert all(record.resolution_status == WordResolutionStatus.UNRESOLVED for record in result.records)
    assert all(not record.approved_forms for record in result.records)
