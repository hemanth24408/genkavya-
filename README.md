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

The system is designed to provide not just generated poetry, but also contextual relevance, word incorporation information, transliteration, meaning, and validation results.

## Key Features

- **AI-Based Sanskrit Poetry Generation:** Generates Sanskrit compositions based on user-provided themes and prescribed words.
- **RAG-Based Contextual Retrieval:** Retrieves relevant information from Ramayana knowledge sources to enrich the generation context.
- **Intelligent Context Summarization:** Uses an LLM to summarize retrieved information and optimize generation prompts.
- **Sanskrit Word Resolution:** Resolves prescribed words into appropriate Sanskrit equivalents before generation.
- **Multiple Candidate Generation:** Generates five candidate compositions for evaluation.
- **Mandatory Word Validation:** Checks the incorporation of all four prescribed words.
- **Metrical Validation:** Evaluates compositions against the selected Classical Anuṣṭubh meter.
- **Duplicate Detection:** Identifies and rejects duplicate compositions.
- **Bounded Generation Retries:** Controls repeated generation attempts.
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

<img width="1928" height="2508" alt="mermaid-diagram (1)" src="https://github.com/user-attachments/assets/d332450e-d5cf-4b5b-baec-02cc405e0d36" />


## Technology Stack

| Category | Technology |
|---|---|
| Frontend Framework | React |
| Frontend Build Tool | Vite |
| Frontend Languages | JavaScript, HTML, CSS |
| Backend | Python |
| AI Model | Qwen 2.5 7B |
| Local Model Runtime | Ollama |
| Knowledge Retrieval | Retrieval-Augmented Generation (RAG) |
| Vector Search | FAISS |
| Data Validation | Pydantic / Custom Validation Modules |
| Testing Framework | Pytest |
| Database | SQLite (prototype persistence) |

## AI Processing Pipeline

### 1. Contextual Knowledge Retrieval

The RAG module retrieves relevant information from the available Ramayana knowledge base based on the user's scene or theme.

The retrieved passages provide contextual evidence to support poetry generation.

### 2. Context Summarization

The retrieved information is passed to the language model to generate a concise contextual summary.

This stage reduces unnecessary prompt content while preserving relevant narrative details.

### 3. Sanskrit Word Resolution

The four prescribed words are interpreted and mapped to appropriate Sanskrit forms using the word-resolution component.

These approved forms are supplied to the generation module.

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

The following represents the intended logical organization of the project. Actual directory names may differ as integration progresses.

```text
GenKavya/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── assets/
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── src/
│   │   └── genkavya/
│   │       ├── api/
│   │       ├── rag/
│   │       ├── words/
│   │       ├── generation/
│   │       ├── validation/
│   │       ├── orchestration/
│   │       └── output/
│   │
│   ├── data/
│   │   ├── knowledge_base/
│   │   ├── lexicon/
│   │   └── vector_index/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── docs/
│   ├── SRS.md
│   ├── FEASIBILITY.md
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_EVOLUTION.md
│
├── .env.example
├── .gitignore
└── README.md
```

## Installation and Setup

### Prerequisites

Ensure the following software is installed:

- Python 3.13 or compatible version.
- Node.js and npm.
- Git.
- Ollama.
- Qwen 2.5 7B model or the model specified in the project configuration.

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd GenKavya
```

### 2. Backend Setup

Create and activate a Python virtual environment.

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install the backend dependencies:

```bash
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

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

---

## Running the Application

### Start the Backend

From the backend project directory, run the configured Python application entry point.

The exact startup command depends on the backend entry point configured in the repository.

### Start the Frontend

From the frontend directory:

```bash
npm run dev
```

Vite will provide a local development URL, typically:

```text
http://localhost:5173
```

Ensure the backend and Ollama services are running before testing the complete application.

---

## Testing

GenKavya uses Pytest for backend unit testing.

Run the complete unit test suite:

```bash
python -m pytest tests/unit -q
```

Run specific generation and AI-related tests:

```bash
python -m pytest tests/unit/test_ollama.py tests/unit/test_contracts_generation.py -q
```

The testing strategy covers:

- Input validation.
- AI model communication.
- Context summarization.
- Sanskrit word resolution.
- Candidate generation.
- Mandatory-word verification.
- Duplicate rejection.
- Meter validation.
- Error handling.

Unit testing and end-to-end integration testing are treated as separate testing activities.

---

## Current Scope and Limitations

- The current Sanskrit word database contains only **4 prescribed-word entries**, limiting word-resolution coverage.
- The RAG knowledge base currently covers **2 Kandas(**&#x42;ala kanda and Aranya kand&#x61;**) of the Ramayana**, restricting contextual retrieval.
- Retrieval accuracy depends on the available documents and may not capture all relevant context.
- The system currently supports four Padas in Pathyā Anuṣṭubh meter.
- Comprehensive Sanskrit grammar verification and advanced Sandhi and Samāsa processing are not yet fully implemented.

## Future Enhancements

- Expand the Sanskrit word database.
- Include all seven Kandas of the Ramayana in the RAG knowledge base.
- Improve retrieval accuracy and contextual summarization.
- Introduce advanced Sanskrit grammar validation and additional meters.
- Improved narrative consistency.
- Expanded Sanskrit literary knowledge sources.

---

## Acknowledgements

GenKavya is an effort to explore the intersection of traditional Sanskrit literature, Avadhana, and modern Artificial Intelligence.

We acknowledge the contributions of open-source AI technologies, language models, knowledge-retrieval frameworks, and Sanskrit literary resources that support this project.

---

**GenKavya – Bringing Sanskrit Creativity into the Age of Artificial Intelligence.**
