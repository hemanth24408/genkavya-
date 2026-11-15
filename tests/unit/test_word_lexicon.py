import json

import pytest

from genkavya.words.lexicon import LexiconError, LexiconRepository


def fixture_document():
    # Synthetic schema fixture only; these tokens and citations assert no Sanskrit facts.
    return {
        "schema_version": "1.0", "lexicon_version": "synthetic-test",
        "references": {"SYN": {"title": "Synthetic test reference", "edition": "fixture", "entry": "test-only"}},
        "entries": [{
            "word_id": "test-word", "english_meanings": ["test term"],
            "lemma": {"base_lemma_id": "test-lemma", "stem_id": "test-stem", "devanagari": "क", "part_of_speech": "noun",
                      "verification": {"status": "verified", "reference_ids": ["SYN"]}},
            "inflections": [{"form_id": "test-form", "devanagari": "कम्", "base_lemma_id": "test-lemma", "stem_id": "test-stem",
                             "grammar": {"case": "synthetic"}, "verification": {"status": "verified", "reference_ids": ["SYN"]}}],
            "derivations": []
        }]
    }


def test_repository_indexes_exact_normalized_meanings():
    repo = LexiconRepository(fixture_document())
    assert len(repo.matches("  TEST   TERM ")) == 1
    assert repo.matches("other") == []


def test_verified_entries_require_real_reference_ids():
    document = fixture_document()
    document["entries"][0]["lemma"]["verification"]["reference_ids"] = ["MISSING"]
    with pytest.raises(LexiconError, match="valid supporting references"):
        LexiconRepository(document)


def test_duplicate_entry_identity_is_rejected():
    document = fixture_document()
    document["entries"].append(document["entries"][0])
    with pytest.raises(LexiconError, match="Duplicate word_id"):
        LexiconRepository(document)


def test_json_path_loader(tmp_path):
    path = tmp_path / "lexicon.json"
    path.write_text(json.dumps(fixture_document()), encoding="utf-8")
    assert LexiconRepository.from_path(path).version == "synthetic-test"
