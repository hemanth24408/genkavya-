"""Controlled, reference-backed Sanskrit word resolution."""

from .lexicon import LexiconRepository, load_default_lexicon
from .resolver import resolve_four_words

__all__ = ["LexiconRepository", "load_default_lexicon", "resolve_four_words"]
