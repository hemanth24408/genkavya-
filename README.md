# GenKavya

### AI-Assisted Sanskrit Dattapadi Poetry Generation System

**Bridging Traditional Sanskrit Literature and Artificial Intelligence**

GenKavya is an AI-powered Sanskrit poetry generation system designed to automate the traditional **Dattapadi challenge** of Avadhana. It combines Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), Sanskrit word processing, and independent poetic validation to generate structured Sanskrit compositions from user-provided themes and four prescribed words.

The project aims to preserve the richness of traditional Sanskrit literary practices while exploring the possibilities of modern Artificial Intelligence.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [AI Processing Pipeline](#ai-processing-pipeline)
- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Current Scope and Limitations](#current-scope-and-limitations)
- [Future Enhancements](#future-enhancements)
- [Acknowledgements](#acknowledgements)

---

## Overview

Dattapadi is a traditional Avadhana challenge in which a poet is required to compose poetry incorporating four prescribed words while maintaining meaningful expression and poetic structure.

GenKavya brings this literary challenge into an AI-assisted environment.

The system accepts:

- A user-defined scene, situation, or theme.
- Four prescribed words that must be incorporated into the composition.

Using contextual knowledge retrieval and AI-based generation, GenKavya produces Sanskrit poetry consisting of four Padas (metrical quarters). Multiple candidate compositions are generated and evaluated against mandatory-word and metrical requirements.

The system is designed to provide generated poetry, contextual relevance, word incorporation information, transliteration, meaning, and validation results.

## Key Features

- **AI-Based Sanskrit Poetry Generation:** Generates Sanskrit compositions based on user-provided themes and prescribed words.
- **RAG-Based Contextual Retrieval:** Retrieves relevant information from Ramayana knowledge sources to enrich generation context.
- **Intelligent Context Summarization:** Uses an LLM to summarize retrieved information and optimize generation prompts.
- **Sanskrit Word Resolution:** Resolves prescribed words into approved Sanskrit forms before generation.
- **Multiple Candidate Generation:** Generates five candidate compositions for evaluation.
- **Mandatory Word Validation:** Checks the incorporation of all four prescribed words.
- **Metrical Validation:** Evaluates compositions against the selected Classical Anuṣṭubh meter.
- **Duplicate Detection:** Identifies duplicate compositions.
- **Structured Output:** Supports Sanskrit poetry, transliteration, English meaning, and validation information.

## How It Works

The application follows a structured processing workflow:

1. **User Input:** The user provides a theme and four prescribed words.
2. **Input Processing:** The backend validates the submitted information.
3. **Word Resolution:** The prescribed words are interpreted and resolved into approved Sanskrit forms.
4. **Context Retrieval:** RAG retrieves relevant information from the Ramayana knowledge base.
5. **Context Summarization:** The retrieved information is summarized using the configured language model.
6. **Poetry Generation:** The generation module uses the original scene, summarized context, and prescribed words to generate five candidate compositions.
7. **Independent Validation:** Each candidate undergoes mandatory-word and metrical checks.
8. **Candidate Classification:** Compositions are evaluated and classified according to validation results.
9. **Result Presentation:** The system prepares the generated poetry and associated information for presentation.

## System Architecture

GenKavya follows a **Modular Monolithic Architecture** with a pipeline-based AI processing design.

The application is organized into the following major components:

| Component | Responsibility |
|---|---|
| Frontend | User interaction and result presentation |
| Backend API | Request handling and application coordination |
| Word Resolution Module | Interpretation and Sanskrit conversion of prescribed words |
| RAG Module | Contextual knowledge retrieval |
| Summarization Module | Compression of retrieved contextual information |
| Generation Module | AI-based Sanskrit poetry generation |
| Validation Module | Mandatory-word and metrical evaluation |
| Data Layer | Knowledge documents, vector index, lexicon and configuration |

### Processing Architecture

<!-- Retain the existing architecture diagram image here if it was present in your previous README. -->

## Technology Stack

| Category | Technology |
|---|---|
| Frontend Framework | React |
| Frontend Build Tool | Vite |
| Frontend Languages | TypeScript, JavaScript, HTML, CSS |
| Backend | Python |
| AI Model | Qwen 2.5 |
| Local Model Runtime | Ollama |
| Knowledge Retrieval | Retrieval-Augmented Generation (RAG) |
| Vector Search | FAISS |
| Data Validation | Pydantic / Custom Validation Modules |
| API Framework | FastAPI |
| Testing Framework | Pytest |

## AI Processing Pipeline

### 1. Contextual Knowledge Retrieval

The RAG module retrieves relevant information from the available Ramayana knowledge base based on the user's scene or theme.

### 2. Context Summarization

The retrieved information is passed to the language model to generate a concise contextual summary.

### 3. Sanskrit Word Resolution

The four prescribed words are interpreted and mapped to appropriate Sanskrit forms using the word-resolution component.

### 4. Poetry Generation

The generation module uses the configured Qwen model through Ollama.

It receives:

- Original user-provided scene.
- Summarized contextual information.
- Four approved Sanskrit word forms.
- Poetry structure and generation constraints.

The module generates five candidate compositions, each intended to contain four Padas.

### 5. Independent Validation

Generated candidates are evaluated independently of the language model.

The validation process focuses on:

- Mandatory-word incorporation.
- Four-Pada structure.
- Syllable count.
- Laghu-Guru classification.
- Applicable Anuṣṭubh metrical patterns.

Validation results are used to classify candidates. Unsupported grammar checks are reported as unverified rather than assumed to be correct.

---

## Project Structure

The project is organized into frontend, backend, data, and test components.

```text
GenKavya/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── services/
│   │   ├── ui/
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
├── src/
│   └── genkavya/
│       ├── api.py
│       ├── contracts/
│       ├── generation/
│       ├── rag/
│       ├── ...
├── data/
├── tests/
│   └── unit/
├── pyproject.toml
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation and Setup

### Prerequisites

Ensure the following software is installed:

- Python 3.13 or compatible version.
- Node.js and npm.
- Git.
- Ollama.
- Qwen 2.5 model configured for the project.

### 1. Clone the Repository

```bash
git clone https://github.com/hemanth24408/genkavya-.git
cd GenKavya
```

### 2. Backend Setup

Create and activate a Python virtual environment.

**Windows PowerShell:**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -e ".[rag,validation,api,dev]"
```

Alternatively, install from the requirements file:

```powershell
pip install -r requirements.txt
```

### 3. AI Model Setup

Install Ollama and download the configured model:

```bash
ollama pull qwen2.5:7b
```

Start the Ollama service and verify its availability:

```bash
ollama list
```

The default local Ollama endpoint is:

```text
http://localhost:11434
```

Ensure that the model name in the project configuration matches the downloaded model.

### 4. Frontend Setup

Navigate to the frontend directory:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

---

## Running the Application

The frontend and backend run separately during local development.

### Start the Backend

Open a terminal in the project root:

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn genkavya.api:app --host 127.0.0.1 --port 8000
```

The backend API will be available at:

```text
http://127.0.0.1:8000
```

### Start the Frontend

Open another terminal:

```powershell
cd frontend
npm.cmd run dev
```

Vite will provide a local development URL, typically:

```text
http://localhost:5173
```

The Vite development server proxies `POST /api/generate` to the backend.

The API accepts a scene and exactly four ordered English words. For example:

```json
{
  "scene": "Rama enters the forest",
  "words": ["forest", "flower", "fruit", "mountain"]
}
```

The endpoint returns the five generated candidates and their independent validation results.

The command-line pipeline can also be run from the project root:

```powershell
$env:PYTHONPATH = "src"
python -m genkavya.pipeline --scene "Rama enters the forest" --words forest flower fruit mountain
```

The command prints the generated candidates and their independent mandatory-word, meter, and grammar evaluation results as JSON.

## Testing

GenKavya uses Pytest for backend unit testing.

Run the complete unit test suite:

```bash
python -m pytest tests/unit -q
```

Run specific generation and API tests:

```bash
python -m pytest tests/unit/test_api.py tests/unit/test_contracts_generation.py tests/unit/test_ollama.py -q
```

The testing strategy covers:

- Input validation.
- API request handling.
- AI model communication.
- Context summarization.
- Sanskrit word resolution.
- Candidate generation.
- Mandatory-word verification.
- Duplicate detection.
- Meter validation.
- Error handling.

Unit testing and end-to-end integration testing are treated as separate testing activities.

---

## Current Scope and Limitations

- The Sanskrit word database has limited prescribed-word coverage.
- The RAG knowledge base currently covers selected portions of the Ramayana.
- Retrieval accuracy depends on the available documents and may not capture all relevant context.
- The system currently supports four Padas in Pathyā Anuṣṭubh meter.
- Comprehensive Sanskrit grammar verification and advanced Sandhi and Samāsa processing are not yet fully implemented.
- Generated candidates may require further linguistic and metrical refinement.

## Future Enhancements

- Expand the Sanskrit word database.
- Include all seven Kandas of the Ramayana in the RAG knowledge base.
- Improve retrieval accuracy and contextual summarization.
- Introduce advanced Sanskrit grammar validation and additional meters.
- Improve narrative consistency.
- Expand Sanskrit literary knowledge sources.

---

## Acknowledgements

GenKavya is an effort to explore the intersection of traditional Sanskrit literature, Avadhana, and modern Artificial Intelligence.

We acknowledge the contributions of open-source AI technologies, language models, knowledge-retrieval frameworks, and Sanskrit literary resources that support this project.

---

**GenKavya – Bringing Sanskrit Creativity into the Age of Artificial Intelligence.**