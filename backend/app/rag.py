"""Séance 3 — chaîne RAG complète : recherche -> contrôle du seuil -> prompt -> LLM -> contrôles."""
import re
import time

from . import indexing
from .prompt import REFUSAL, SYSTEM_PROMPT, build_user_message

CITATION = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")


def extract_citations(answer: str) -> list[int]:
    """'[1]', '[2, 3]' -> [1, 2, 3] (dans l'ordre d'apparition, sans doublon)."""
    seen: list[int] = []
    for m in CITATION.finditer(answer):
        for n in re.findall(r"\d+", m.group(1)):
            if int(n) not in seen:
                seen.append(int(n))
    return seen


def normalize_citations(answer: str) -> str:
    """Certains modèles écrivent « 【2】 » (crochets pleine chasse) au lieu de « [2] » : on les ramène
    au format attendu, sinon une bonne réponse est prise pour une réponse sans citation."""
    return re.sub(r"【\s*(\d+(?:\s*[,;]\s*\d+)*)\s*】", r"[\1]", answer)


def is_refusal(answer: str) -> bool:
    norm = lambda s: s.replace("’", "'").lower()
    return norm(REFUSAL) in norm(answer)


def add_amending_fragments(client, embedder, question, hits, strategy, threshold) -> list[dict]:
    """Règle des versions, sans rien coder en dur pour ce corpus : si un fragment retrouvé vient
    d'un document qui est modifié par un autre (champ `amends` lu dans les métadonnées), on va aussi
    chercher les fragments pertinents du document modificatif."""
    docs = indexing.list_documents(client, strategy)
    amended_by = {d["amends"]: d["reference"] for d in docs if d["amends"]}
    present = {h["chunk_id"] for h in hits}
    extra = []
    for ref in sorted({h["reference"] for h in hits} & amended_by.keys()):
        for h in indexing.search(client, embedder, question, 2, strategy, reference=amended_by[ref]):
            if h["chunk_id"] not in present and h["score"] >= threshold:
                extra.append(h)
                present.add(h["chunk_id"])
    return sorted(hits + extra, key=lambda h: h["score"], reverse=True)


def _refusal(started: float, reason: str = "", raw: str = "") -> dict:
    # `refusal_reason` et `raw_answer` servent au diagnostic (eval/run_eval.py) ; le contrat de
    # l'API (AskResponse) ne les expose pas.
    return {"answer": REFUSAL, "found": False, "sources": [],
            "invalid_citations": [], "latency_ms": int((time.perf_counter() - started) * 1000),
            "refusal_reason": reason, "raw_answer": raw}


def ask(client, embedder, llm, question: str, top_k: int, strategy: str, doc_type: str | None,
        score_threshold: float) -> dict:
    started = time.perf_counter()
    hits = indexing.search(client, embedder, question, top_k, strategy, doc_type)

    # Contrôle n°1 (côté code) : meilleur score trop bas -> refus SANS appeler le LLM.
    if not hits or hits[0]["score"] < score_threshold:
        return _refusal(started, "below_threshold")

    hits = add_amending_fragments(client, embedder, question, hits, strategy, score_threshold)
    answer = normalize_citations(llm.chat(SYSTEM_PROMPT, build_user_message(question, hits)))

    # Refus décidé par le LLM : on normalise la phrase pour qu'elle soit exacte.
    if is_refusal(answer):
        return _refusal(started, "llm_refusal", answer)

    # Contrôle n°2 (côté code) : chaque numéro cité doit correspondre à un fragment fourni.
    cited = extract_citations(answer)
    invalid = sorted(n for n in cited if not 1 <= n <= len(hits))

    # Contrôle n°3 : une réponse fondée cite au moins un fragment valide. Sans citation valide,
    # le modèle a répondu « de mémoire » ou a reformulé son refus : on traite cela comme un refus.
    if len(cited) == len(invalid):
        return _refusal(started, "no_valid_citation", answer)

    sources = [{
        "id": i, "chunk_id": h["chunk_id"], "file": h["file"], "reference": h["reference"],
        "date": h["date"], "page": h["page"], "section": h["section"],
        "excerpt": h["content"][:300] + ("…" if len(h["content"]) > 300 else ""),
        "score": h["score"],
    } for i, h in enumerate(hits, start=1)]
    return {"answer": answer, "found": True, "sources": sources, "invalid_citations": invalid,
            "latency_ms": int((time.perf_counter() - started) * 1000)}
