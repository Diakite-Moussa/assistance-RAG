"""Séance 2 — indexation idempotente dans Chroma et recherche par similarité."""
from pathlib import Path

from .chunking import chunk_corpus
from .config import settings
from .extract import extract_corpus

BATCH = 64


def collection_name(strategy: str) -> str:
    # une collection par stratégie : on peut comparer fixe/structurel à la séance 5
    return f"{settings.collection_name}_{strategy}"


def get_collection(client, strategy: str):
    # distance cosinus : score = 1 - distance (1 = identique)
    return client.get_or_create_collection(
        name=collection_name(strategy), configuration={"hnsw": {"space": "cosine"}}
    )


def embedding_text(chunk: dict) -> str:
    """Texte réellement vectorisé : on ajoute le titre du document et la section au contenu."""
    return f"{chunk['title']} | {chunk['section']}\n{chunk['content']}"


def _metadata(chunk: dict) -> dict:
    meta = {k: v for k, v in chunk.items() if k != "content"}
    meta["date_num"] = int(chunk["date"].replace("-", "")) if chunk["date"] else 0
    return meta


def ingest(client, embedder, strategy: str, size: int, overlap: int, max_chars: int,
           corpus_dir: Path | None = None) -> dict:
    """(Ré)indexe le corpus. Idempotent : upsert sur des identifiants stables,
    et suppression des fragments devenus obsolètes."""
    docs = extract_corpus(corpus_dir or settings.corpus_dir)
    chunks = chunk_corpus(docs, strategy, size, overlap, max_chars)
    col = get_collection(client, strategy)

    new_ids = {c["id"] for c in chunks}
    stale = list(set(col.get(include=[])["ids"]) - new_ids)
    if stale:
        col.delete(ids=stale)

    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        col.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["content"] for c in batch],
            embeddings=embedder.embed_passages([embedding_text(c) for c in batch]),
            metadatas=[_metadata(c) for c in batch],
        )
    return {"strategy": strategy, "documents": len(docs), "chunks": len(chunks),
            "removed": len(stale), "total_in_index": col.count()}


def _where(doc_type: str | None, reference: str | None):
    conditions = []
    if doc_type:
        conditions.append({"type": doc_type})
    if reference:
        conditions.append({"reference": reference})
    if not conditions:
        return None
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def search(client, embedder, query: str, top_k: int, strategy: str, doc_type: str | None = None,
           reference: str | None = None) -> list[dict]:
    col = get_collection(client, strategy)
    total = col.count()
    if total == 0:
        return []
    res = col.query(
        query_embeddings=[embedder.embed_query(query)],
        n_results=min(top_k, total),
        where=_where(doc_type, reference),
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0],
                                    res["distances"][0]):
        hits.append({**meta, "chunk_id": cid, "content": doc, "score": round(1 - dist, 4)})
    return hits


def list_documents(client, strategy: str) -> list[dict]:
    col = get_collection(client, strategy)
    docs: dict[str, dict] = {}
    for meta in col.get(include=["metadatas"])["metadatas"]:
        d = docs.setdefault(meta["reference"], {
            "file": meta["file"], "title": meta["title"], "reference": meta["reference"],
            "type": meta["type"], "date": meta["date"], "version": meta["version"],
            "status": meta["status"], "amends": meta["amends"], "chunks": 0,
        })
        d["chunks"] += 1
    return sorted(docs.values(), key=lambda d: d["file"])