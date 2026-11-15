import re

import pytest

from genkavya.config import Settings
from genkavya.contracts.generation import SANSKRIT_CANDIDATE_OUTPUT_SCHEMA
from genkavya.generation import ollama


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


def test_ollama_uses_central_settings_and_json_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(ollama.httpx, "post", lambda *args, **kwargs: (
        calls.append((args, kwargs)) or Response({"response": "{}"})
    ))
    settings = Settings(_env_file=None, ollama_model="qwen2.5:7b", request_timeout_seconds=12)
    assert ollama.generate_json("prompt", settings=settings) == "{}"
    args, kwargs = calls[0]
    assert args[0].endswith("/api/generate")
    assert kwargs["json"]["model"] == "qwen2.5:7b"
    assert kwargs["json"]["format"] == "json"
    assert kwargs["json"]["stream"] is False
    assert kwargs["timeout"] == 12


def test_ollama_text_mode_omits_response_format(monkeypatch):
    calls = []
    monkeypatch.setattr(ollama.httpx, "post", lambda *args, **kwargs: (
        calls.append((args, kwargs)) or Response({"response": "A concise summary."})
    ))
    settings = Settings(_env_file=None, ollama_model="qwen2.5:7b")
    assert ollama.generate_text("summary prompt", settings=settings) == "A concise summary."
    payload = calls[0][1]["json"]
    assert payload["model"] == "qwen2.5:7b"
    assert "format" not in payload


def test_poetry_generation_keeps_json_response_format(monkeypatch):
    calls = []
    monkeypatch.setattr(ollama.httpx, "post", lambda *args, **kwargs: (
        calls.append(kwargs["json"]) or Response({"response": "{}"})
    ))
    ollama.generate_json("poetry prompt", settings=Settings(_env_file=None))
    assert calls[0]["format"] == "json"


def test_ollama_passes_json_schema_object_as_format(monkeypatch):
    calls = []
    monkeypatch.setattr(ollama.httpx, "post", lambda *args, **kwargs: (
        calls.append(kwargs["json"]) or Response({"response": "{}"})
    ))
    ollama.generate_json(
        "poetry prompt", settings=Settings(_env_file=None),
        schema=SANSKRIT_CANDIDATE_OUTPUT_SCHEMA,
    )
    assert calls[0]["format"] == SANSKRIT_CANDIDATE_OUTPUT_SCHEMA
    assert calls[0]["format"]["properties"]["padas"]["minItems"] == 4
    assert calls[0]["format"]["properties"]["padas"]["maxItems"] == 4
    assert calls[0]["format"]["properties"]["padas"]["items"] == {
        "type": "string", "minLength": 1, "pattern": "^(?!.*[\\r\\n])[^\\r\\n]+$",
    }
    pada_pattern = calls[0]["format"]["properties"]["padas"]["items"]["pattern"]
    assert re.search(pada_pattern, "single line")
    for line_break in ("\n", "\r"):
        assert re.search(pada_pattern, f"first{line_break}second") is None
        assert re.search(pada_pattern, f"single line{line_break}") is None
    assert calls[0]["format"]["properties"]["english_summary"] == {
        "type": "string", "minLength": 1,
    }
    assert calls[0]["format"]["required"] == ["padas", "english_summary"]
    assert calls[0]["format"]["additionalProperties"] is False


def test_ollama_rejects_missing_response_text(monkeypatch):
    monkeypatch.setattr(ollama.httpx, "post", lambda *args, **kwargs: Response({"done": True}))
    with pytest.raises(ollama.OllamaError, match="response"):
        ollama.generate_json("prompt", settings=Settings(_env_file=None))


def test_ollama_wraps_http_failures(monkeypatch):
    def fail(*args, **kwargs):
        raise ollama.httpx.ConnectError("offline")

    monkeypatch.setattr(ollama.httpx, "post", fail)
    with pytest.raises(ollama.OllamaError, match="offline"):
        ollama.generate_json("prompt", settings=Settings(_env_file=None))
