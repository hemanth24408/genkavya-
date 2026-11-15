"""Modular Sanskrit candidate generation through Ollama."""

from .generator import GenerationError, generate_candidates

__all__ = ["GenerationError", "generate_candidates"]
