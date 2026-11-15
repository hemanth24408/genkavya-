"""Small Ollama JSON-generation transport using centralized settings."""

from __future__ import annotations

from typing import Any

import httpx

from genkavya.config import Settings, get_settings


class OllamaError(RuntimeError):
    """Ollama could not return a usable generation response."""


def _generate(
    prompt: str,
    *,
    response_format: str | dict[str, Any] | None,
    settings: Settings | None = None,
) -> str:
    """Call Ollama's local generate endpoint with an optional response format."""
    if not prompt.strip():
        raise ValueError("Generation prompt cannot be empty")
    settings = settings or get_settings()
    if settings.llm_provider != "ollama":
        raise OllamaError(f"Unsupported LLM provider: {settings.llm_provider}")
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    if response_format is not None:
        payload["format"] = response_format
    url = f"{str(settings.ollama_base_url).rstrip('/')}/api/generate"
    try:
        response = httpx.post(url, json=payload, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OllamaError(f"Ollama generation request failed: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("response"), str):
        raise OllamaError("Ollama response did not contain text in the 'response' field")
    return data["response"]


def generate_json(
    prompt: str,
    *,
    settings: Settings | None = None,
    schema: dict[str, Any] | None = None,
) -> str:
    """Call Ollama in JSON mode or constrain output with a JSON Schema."""
    response_format = schema if schema is not None else "json"
    return _generate(prompt, response_format=response_format, settings=settings)


def generate_text(prompt: str, *, settings: Settings | None = None) -> str:
    """Call Ollama without a response-format constraint (used for summaries)."""
    return _generate(prompt, response_format=None, settings=settings)
