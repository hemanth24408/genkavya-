"""Local FastAPI interface for the modular GenKavya pipeline."""

from fastapi import FastAPI, HTTPException
from pydantic import Field, model_validator

from genkavya.contracts.common import ContractModel
from genkavya.pipeline import run_generation_report, serialize_generation_report


class GenerateRequest(ContractModel):
    """Scene and four ordered English mandatory-word positions."""

    scene: str = Field(min_length=1)
    words: tuple[str, str, str, str]

    @model_validator(mode="after")
    def require_nonempty_inputs(self):
        if not self.scene.strip():
            raise ValueError("Scene must contain non-whitespace text")
        if any(not word.strip() for word in self.words):
            raise ValueError("All four mandatory words must contain non-whitespace text")
        return self


app = FastAPI(title="GenKavya API", version="0.1.0")


@app.post("/api/generate")
def generate(request: GenerateRequest) -> dict:
    """Run RAG, word resolution, generation, and validation once through the coordinator."""
    try:
        generation, validation = run_generation_report(request.scene, request.words)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return serialize_generation_report(generation, validation)
