"""API FastAPI — toutes les routes sont préfixées par /api ; documentation sur /docs.
Lancer (depuis la racine) : uv run uvicorn app.main:app --reload --app-dir backend"""
from functools import lru_cache

import chromadb
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import indexing, rag
from .config import settings
from .embeddings import Embedder
from .llm import GroqClient, LLMUnavailable
from .schemas import (AskRequest, AskResponse, DocumentInfo, HealthResponse, IngestRequest,
                      IngestResponse, SearchHit, SearchRequest, SearchResponse)


@lru_cache
def get_embedder() -> Embedder:
    return Embedder(settings.embedding_model)


@lru_cache
def get_client():
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


@lru_cache
def get_llm() -> GroqClient:
    return GroqClient(settings.groq_api_key, settings.groq_model, settings.groq_base_url,
                      settings.llm_timeout)


app = FastAPI(title="Assistant Scolarité EIH", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
api = APIRouter(prefix="/api")


@api.get("/health", response_model=HealthResponse)
def health(client=Depends(get_client)):
    try:
        count = indexing.get_collection(client, settings.chunk_strategy).count()
    except Exception as exc:  # base vectorielle indisponible
        raise HTTPException(status_code=503, detail=f"Base vectorielle indisponible : {exc}")
    return HealthResponse(status="ok", strategy=settings.chunk_strategy, chunks=count)


@api.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest, client=Depends(get_client), embedder=Depends(get_embedder)):
    return indexing.ingest(client, embedder, req.strategy, req.chunk_size, req.chunk_overlap,
                           req.max_section_chars)


@api.get("/documents", response_model=list[DocumentInfo])
def documents(strategy: str | None = None, client=Depends(get_client)):
    return indexing.list_documents(client, strategy or settings.chunk_strategy)


@api.post("/search", response_model=SearchResponse)
def search(req: SearchRequest, client=Depends(get_client), embedder=Depends(get_embedder)):
    hits = indexing.search(client, embedder, req.question, req.top_k,
                           req.strategy or settings.chunk_strategy, req.filters.type)
    return SearchResponse(hits=[SearchHit(**h) for h in hits])


@api.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, client=Depends(get_client), embedder=Depends(get_embedder), llm=Depends(get_llm)):
    try:
        return rag.ask(client, embedder, llm, req.question, req.top_k,
                       req.strategy or settings.chunk_strategy, req.filters.type,
                       settings.score_threshold)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=502, detail=f"Le modèle de langage ne répond pas : {exc}")


app.include_router(api)