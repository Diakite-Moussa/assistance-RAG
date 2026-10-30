"""Configuration centrale : valeurs par défaut + surcharge par le fichier .env."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]  # racine du projet (assistant-scolarite/)
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    corpus_dir: Path = ROOT / "data" / "corpus"
    output_dir: Path = ROOT / "data"
    chunk_strategy: str = os.getenv("CHUNK_STRATEGY", "structural")  # fixed | structural
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    max_section_chars: int = int(os.getenv("MAX_SECTION_CHARS", "900"))
    embedding_model: str = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")
    chroma_dir: Path = ROOT / os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "eih_scolarite")
    top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:4200")
    score_threshold: float = float(os.getenv("SCORE_THRESHOLD", "0.83"))
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "60"))

settings = Settings()