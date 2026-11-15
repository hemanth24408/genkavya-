# GenKavya

GenKavya is a modular Sanskrit poetry generation project. Its Python package is in `src/genkavya/`; Ramayana corpus assets remain under `modules/ramayana_kb/data/` and the controlled word lexicon is `data/lexicon/words.json`.

## Setup

Use Python 3.13 and install the project with the dependencies for the local pipeline:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[rag,validation,dev]"
```

Configure the local Ollama endpoint and model through the environment settings documented in `.env.example`. The configured model is used by the existing summarization and poetry-generation steps.

## Run

From the project root, set `PYTHONPATH=src` and pass one scene plus exactly four mandatory English words:

```powershell
$env:PYTHONPATH = "src"
python -m genkavya.pipeline --scene "Describe a Ramayana scene" --words forest flower fruit mountain
```

The command prints the generated candidates and their independent mandatory-word, meter, and grammar evaluation results as JSON. Poetry generation uses five candidates with one model request per candidate; evaluation results do not remove structurally parsed candidates.
