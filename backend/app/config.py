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


settings = Settings()