"""Modèles Pydantic de l'API (validation -> 422 automatique si invalide)."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from .config import settings

Strategy = Literal["fixed", "structural"]


class IngestRequest(BaseModel):
    strategy: Strategy = settings.chunk_strategy
    chunk_size: int = Field(settings.chunk_size, ge=100, le=4000)
    chunk_overlap: int = Field(settings.chunk_overlap, ge=0, le=2000)
    max_section_chars: int = Field(settings.max_section_chars, ge=200, le=5000)

    @model_validator(mode="after")
    def overlap_below_size(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap doit être strictement inférieur à chunk_size")
        return self


class Filters(BaseModel):
    type: str | None = None


class SearchRequest(BaseModel):
    question: str
    top_k: int = Field(5, ge=1, le=20)
    filters: Filters = Field(default_factory=Filters)
    strategy: Strategy | None = None  # par défaut : la stratégie configurée

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("la question ne peut pas être vide")
        return v


class SearchHit(BaseModel):
    chunk_id: str
    file: str
    reference: str
    type: str
    date: str
    page: int
    section: str
    content: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class IngestResponse(BaseModel):
    strategy: Strategy
    documents: int
    chunks: int
    removed: int
    total_in_index: int


class DocumentInfo(BaseModel):
    file: str
    title: str
    reference: str
    type: str
    date: str
    version: str
    status: str
    amends: str
    chunks: int


class HealthResponse(BaseModel):
    status: str
    strategy: Strategy
    chunks: int

class AskRequest(BaseModel):
    question: str
    top_k: int = Field(settings.top_k, ge=1, le=20)
    filters: Filters = Field(default_factory=Filters)
    strategy: Strategy | None = None

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("la question ne peut pas être vide")
        return v


class Source(BaseModel):
    id: int
    chunk_id: str
    file: str
    reference: str
    date: str
    page: int
    section: str
    excerpt: str
    score: float


class AskResponse(BaseModel):
    answer: str
    found: bool
    sources: list[Source]
    invalid_citations: list[int]
    latency_ms: int    