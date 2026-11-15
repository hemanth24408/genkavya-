"""Configuration for the existing Ramayana FAISS corpus and model."""

from pathlib import Path

from genkavya.contracts.rag import RetrievalScoreMetadata

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_CHUNKS_DIR = PROJECT_ROOT / "modules" / "ramayana_kb" / "data" / "processed_chunks"
VECTOR_DIR = PROJECT_ROOT / "modules" / "ramayana_kb" / "data" / "vector_store"
INDEX_PATH = VECTOR_DIR / "ramayana.index"
METADATA_PATH = VECTOR_DIR / "metadata.json"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SOURCE_ID = "VALMIKI_RAMAYANA_DUTT"
WORK = "The Ramayana of Valmiki"
TRANSLATOR = "Manmatha Nath Dutt"
ALLOWED_KANDAS = {"Bala Kanda", "Aranya Kanda"}
KANDA_CONTRACT_LABELS = {
    "Bala Kanda": "Bāla Kāṇḍa",
    "Aranya Kanda": "Araṇya Kāṇḍa",
}
FAISS_METRIC = "inner_product"
EMBEDDING_NORMALIZED = True
SCORE_INTERPRETATION = "cosine_similarity_equivalent"


def score_metadata() -> RetrievalScoreMetadata:
    return RetrievalScoreMetadata(
        metric=FAISS_METRIC,
        embedding_normalized=EMBEDDING_NORMALIZED,
        interpretation=SCORE_INTERPRETATION,
    )

