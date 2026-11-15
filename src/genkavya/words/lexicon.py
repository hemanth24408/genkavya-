"""Read-only repository for the controlled Sanskrit JSON lexicon."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from genkavya.contracts.common import VerificationStatus


class LexiconError(ValueError):
    """The lexicon is malformed or contains conflicting identifiers/references."""


def normalize_english(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


class LexiconRepository:
    """Validated, in-memory view of a versioned JSON vocabulary."""

    def __init__(self, document: dict[str, Any]):
        if not isinstance(document, dict) or not isinstance(document.get("entries"), list):
            raise LexiconError("Lexicon must contain an entries array")
        self.version = str(document.get("lexicon_version", "")).strip()
        if not self.version:
            raise LexiconError("Lexicon must declare lexicon_version")
        self.references = document.get("references", {})
        if not isinstance(self.references, dict):
            raise LexiconError("references must be an object")
        for ref_id, ref in self.references.items():
            if not isinstance(ref, dict) or not all(str(ref.get(k, "")).strip() for k in ("title", "edition")):
                raise LexiconError(f"Reference {ref_id!r} requires title and edition")
            if not any(str(ref.get(k, "")).strip() for k in ("entry", "page", "url")):
                raise LexiconError(f"Reference {ref_id!r} needs an entry, page, or URL")
        self.entries = document["entries"]
        self._terms: dict[str, list[dict[str, Any]]] = {}
        seen_words: set[str] = set()
        seen_lemmas: set[str] = set()
        for entry in self.entries:
            self._validate_entry(entry)
            word_id = entry["word_id"]
            lemma = entry["lemma"]
            if word_id in seen_words:
                raise LexiconError(f"Duplicate word_id: {word_id}")
            seen_words.add(word_id)
            if lemma["base_lemma_id"] in seen_lemmas:
                raise LexiconError(f"Duplicate base_lemma_id: {lemma['base_lemma_id']}")
            seen_lemmas.add(lemma["base_lemma_id"])
            for term in entry["english_meanings"]:
                key = normalize_english(term)
                if key:
                    self._terms.setdefault(key, []).append(entry)

    @classmethod
    def from_path(cls, path: str | Path) -> "LexiconRepository":
        try:
            with Path(path).open(encoding="utf-8") as stream:
                return cls(json.load(stream))
        except (OSError, json.JSONDecodeError) as exc:
            raise LexiconError(f"Cannot load lexicon {path}: {exc}") from exc

    def matches(self, english: str) -> list[dict[str, Any]]:
        """Return all entries matching the normalized English lookup key."""
        return list(self._terms.get(normalize_english(english), ()))

    def reference_text(self, reference_ids: list[str]) -> str | None:
        """Render traceable citation details; None means not fully resolvable."""
        parts: list[str] = []
        for ref_id in reference_ids:
            ref = self.references.get(ref_id)
            if not ref:
                return None
            locator = "; ".join(f"{key}: {ref[key]}" for key in ("entry", "page", "url") if ref.get(key))
            parts.append(f"{ref['title']} ({ref['edition']}) — {locator}")
        return " | ".join(parts) or None

    def _validate_entry(self, entry: Any) -> None:
        if not isinstance(entry, dict):
            raise LexiconError("Each lexicon entry must be an object")
        required = ("word_id", "english_meanings", "lemma", "inflections", "derivations")
        if any(key not in entry for key in required):
            raise LexiconError(f"Entry is missing one of {required}")
        if not isinstance(entry["english_meanings"], list) or not entry["english_meanings"]:
            raise LexiconError(f"Entry {entry['word_id']} requires English lookup terms")
        lemma = entry["lemma"]
        if not isinstance(lemma, dict) or any(not str(lemma.get(k, "")).strip() for k in ("base_lemma_id", "stem_id", "devanagari", "part_of_speech")):
            raise LexiconError(f"Entry {entry['word_id']} has incomplete lemma identity")
        self._check_verification(lemma.get("verification"), f"lemma {lemma['base_lemma_id']}")
        if not isinstance(entry["inflections"], list) or not isinstance(entry["derivations"], list):
            raise LexiconError(f"Entry {entry['word_id']} forms must be arrays")
        for kind, forms in (("inflection", entry["inflections"]), ("derivation", entry["derivations"])):
            ids: set[str] = set()
            for form in forms:
                if not isinstance(form, dict) or any(not str(form.get(k, "")).strip() for k in ("form_id", "devanagari", "base_lemma_id", "stem_id")):
                    raise LexiconError(f"Entry {entry['word_id']} has an incomplete {kind}")
                if form["base_lemma_id"] != lemma["base_lemma_id"] or form["stem_id"] != lemma["stem_id"]:
                    raise LexiconError(f"Form {form['form_id']} does not trace to its entry lemma and stem")
                if form["form_id"] in ids:
                    raise LexiconError(f"Duplicate form_id {form['form_id']} in entry {entry['word_id']}")
                ids.add(form["form_id"])
                if kind == "derivation" and not isinstance(form.get("derivation_relationship"), dict):
                    raise LexiconError(f"Derived form {form['form_id']} requires derivation_relationship")
                self._check_verification(form.get("verification"), f"form {form['form_id']}")

    def _check_verification(self, verification: Any, label: str) -> None:
        if not isinstance(verification, dict) or verification.get("status") not in {s.value for s in VerificationStatus}:
            raise LexiconError(f"{label} has invalid verification status")
        ref_ids = verification.get("reference_ids", [])
        if not isinstance(ref_ids, list):
            raise LexiconError(f"{label} reference_ids must be an array")
        if verification["status"] == VerificationStatus.VERIFIED.value:
            if not ref_ids or self.reference_text(ref_ids) is None:
                raise LexiconError(f"Verified {label} requires valid supporting references")


def load_default_lexicon() -> LexiconRepository:
    return LexiconRepository.from_path(Path(__file__).resolve().parents[3] / "data" / "lexicon" / "words.json")
