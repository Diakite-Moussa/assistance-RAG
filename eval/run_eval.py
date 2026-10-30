"""Séance 5 — évaluation du RAG sur un jeu de test dont les réponses viennent des documents.

Deux niveaux de mesure :
  1. RETRIEVAL (sans LLM, rapide, gratuit) : le bon fragment est-il retrouvé dans le top-k ?
       any@k : au moins une des preuves attendues est dans le top-k
       all@k : toutes les preuves attendues sont dans le top-k (cas multi-fragments)
       MRR   : moyenne de 1 / rang du premier fragment pertinent
       seuil : faux refus (question valide sous le seuil) et refus corrects (hors corpus)
  2. BOUT EN BOUT (--llm, appelle Groq) : la réponse est-elle juste et sourcée ?
       décision « trouvé / refus » conforme à l'attendu
       mots-clés attendus présents (proxy automatique : relire aussi les réponses du rapport JSON)
       citations valides, et document modificatif cité quand il le faut

Usage (depuis la racine du projet) :
    uv run python eval/run_eval.py                          # retrieval : structural vs fixed
    uv run python eval/run_eval.py --strategies structural --llm

Le rapport détaillé (réponses du LLM comprises) est écrit dans eval/results/.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import chromadb  # noqa: E402

from app import indexing, rag  # noqa: E402
from app.config import settings  # noqa: E402
from app.embeddings import Embedder  # noqa: E402
from app.llm import GroqClient, LLMUnavailable  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------- utilitaires ----------

def norm(text: str) -> str:
    """Minuscules, sans accents, sans espaces ni ponctuation : robuste aux retours à la ligne
    des fragments et aux variantes d'espaces (« 28 000 » = « 28000 »)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def as_list(x) -> list:
    return x if isinstance(x, list) else [x]


def contains(text: str, needle: str) -> bool:
    return norm(needle) in norm(text)


def need_met(need: dict, hit: dict) -> bool:
    refs = need.get("reference")
    if refs and hit["reference"] not in as_list(refs):
        return False
    return any(contains(hit["content"], alt) for alt in as_list(need["contains"]))


def keywords_ok(answer: str, keywords: list) -> bool:
    return all(any(contains(answer, alt) for alt in as_list(k)) for k in keywords)


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f} %)" if b else "n/a"


def ensure_index(client, embedder, strategy: str) -> None:
    if indexing.get_collection(client, strategy).count() == 0:
        print(f"Index « {strategy} » vide : indexation en cours (quelques instants)...")
        indexing.ingest(client, embedder, strategy, settings.chunk_size, settings.chunk_overlap,
                        settings.max_section_chars)


# ---------- niveau 1 : retrieval ----------

def retrieval_eval(client, embedder, strategy: str, questions: list, ks: list) -> list:
    rows = []
    kmax = max(ks)
    for q in questions:
        hits = indexing.search(client, embedder, q["question"], kmax, strategy)
        best = hits[0]["score"] if hits else 0.0
        row = {"id": q["id"], "category": q["category"], "question": q["question"],
               "expect_found": q["expect_found"], "best_score": best,
               "refused_by_threshold": best < settings.score_threshold}
        if q["expect_found"]:
            needs = q["evidence"]
            row["rank"] = next((i for i, h in enumerate(hits, 1)
                                if any(need_met(n, h) for n in needs)), None)
            for k in ks:
                top = hits[:k]
                row[f"any@{k}"] = any(need_met(n, h) for n in needs for h in top)
                row[f"all@{k}"] = all(any(need_met(n, h) for h in top) for n in needs)
        rows.append(row)
    return rows


def print_retrieval(rows: list, ks: list) -> None:
    ans = [r for r in rows if r["expect_found"]]
    print(f"\n--- Retrieval (seuil actuel : {settings.score_threshold}) ---")
    for k in ks:
        print(f"any@{k}: {pct(sum(r[f'any@{k}'] for r in ans), len(ans))}   "
              f"all@{k}: {pct(sum(r[f'all@{k}'] for r in ans), len(ans))}")
    mrr = sum(1 / r["rank"] for r in ans if r["rank"]) / len(ans)
    print(f"MRR: {mrr:.3f}")
    print(f"Faux refus par le seuil (questions valides) : "
          f"{pct(sum(r['refused_by_threshold'] for r in ans), len(ans))}")
    for cat in ("out_of_corpus", "same_topic_no_answer"):
        sub = [r for r in rows if r["category"] == cat]
        note = "attendu élevé" if cat == "out_of_corpus" else "info : le prompt doit refuser le reste"
        print(f"Refusés par le seuil, {cat} : "
              f"{pct(sum(r['refused_by_threshold'] for r in sub), len(sub))} ({note})")
    print("\nPar catégorie (any@%d) :" % max(ks))
    for cat in sorted({r["category"] for r in ans}):
        sub = [r for r in ans if r["category"] == cat]
        print(f"  {cat:<16} {pct(sum(r[f'any@{max(ks)}'] for r in sub), len(sub))}")
    missed = [r for r in ans if not r[f"all@{max(ks)}"]]
    if missed:
        print(f"\nÀ examiner (preuves manquantes dans le top-{max(ks)}) :")
        for r in missed:
            print(f"  {r['id']} rang={r['rank']} score={r['best_score']:.3f}  {r['question'][:70]}")


# ---------- niveau 2 : bout en bout ----------

def llm_eval(client, embedder, llm, strategy: str, questions: list, sleep: float) -> list:
    rows = []
    for q in questions:
        res, err = None, None
        for _ in range(2):  # une nouvelle tentative (limite de requêtes Groq)
            try:
                res = rag.ask(client, embedder, llm, q["question"], settings.top_k, strategy,
                              None, settings.score_threshold)
                err = None
                break
            except LLMUnavailable as exc:
                err = str(exc)
                time.sleep(30)
        row = {"id": q["id"], "category": q["category"], "question": q["question"],
               "expect_found": q["expect_found"], "expected_answer": q["expected_answer"]}
        if err:
            row["error"] = err
            rows.append(row)
            continue
        cited = rag.extract_citations(res["answer"])
        refs_cited = {res["sources"][n - 1]["reference"] for n in cited
                      if 1 <= n <= len(res["sources"])}
        row.update({
            "answer": res["answer"], "found": res["found"], "latency_ms": res["latency_ms"],
            "decision_ok": res["found"] == q["expect_found"],
            "invalid_citations": res["invalid_citations"],
            "references_cited": sorted(refs_cited),
            "refusal_reason": res.get("refusal_reason", ""),
            "raw_answer": res.get("raw_answer", ""),
        })
        if q["expect_found"]:
            row["keywords_ok"] = res["found"] and keywords_ok(res["answer"], q["answer_keywords"])
            row["citations_ok"] = res["found"] and bool(cited) and not res["invalid_citations"]
            if q.get("must_cite"):
                row["must_cite_ok"] = set(q["must_cite"]) <= refs_cited
        rows.append(row)
        time.sleep(sleep)
    return rows


def print_llm(rows: list) -> None:
    ok = [r for r in rows if "error" not in r]
    errors = [r for r in rows if "error" in r]
    ans = [r for r in ok if r["expect_found"]]
    ref = [r for r in ok if not r["expect_found"]]
    print("\n--- Bout en bout (LLM) ---")
    print(f"Décision trouvé/refus correcte : {pct(sum(r['decision_ok'] for r in ok), len(ok))}")
    print(f"Questions valides répondues    : {pct(sum(r['found'] for r in ans), len(ans))}")
    print(f"Mots-clés attendus présents    : {pct(sum(r['keywords_ok'] for r in ans), len(ans))}")
    print(f"Citations valides              : {pct(sum(r['citations_ok'] for r in ans), len(ans))}")
    mc = [r for r in ans if "must_cite_ok" in r]
    print(f"Document modificatif cité      : {pct(sum(r['must_cite_ok'] for r in mc), len(mc))}")
    for cat in ("out_of_corpus", "same_topic_no_answer"):
        sub = [r for r in ref if r["category"] == cat]
        print(f"Refus corrects, {cat:<21}: {pct(sum(not r['found'] for r in sub), len(sub))}")
    if ok:
        print(f"Latence moyenne : {sum(r['latency_ms'] for r in ok) / len(ok):.0f} ms")
    bad = [r for r in ok if not r["decision_ok"] or r.get("keywords_ok") is False
           or r.get("citations_ok") is False or r.get("must_cite_ok") is False]
    if bad:
        print("\nÀ relire dans le rapport JSON :")
        for r in bad:
            flags = [k for k in ("decision_ok", "keywords_ok", "citations_ok", "must_cite_ok")
                     if r.get(k) is False]
            print(f"  {r['id']} ({r['category']}) échecs : {', '.join(flags)}"
                  f"  [cause du refus : {r.get('refusal_reason') or '-'}]")
    for r in errors:
        print(f"  {r['id']} ERREUR LLM : {r['error']}")


# ---------- programme principal ----------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.json"))
    ap.add_argument("--strategies", nargs="+", default=["structural", "fixed"],
                    choices=["fixed", "structural"])
    ap.add_argument("--ks", nargs="+", type=int, default=[1, 3, 5])
    ap.add_argument("--llm", action="store_true", help="évaluation bout en bout (appelle Groq)")
    ap.add_argument("--sleep", type=float, default=3.0, help="pause entre deux appels LLM (s)")
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["questions"]
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    embedder = Embedder(settings.embedding_model)
    llm = (GroqClient(settings.groq_api_key, settings.groq_model, settings.groq_base_url,
                      settings.llm_timeout) if args.llm else None)

    report = {"date": datetime.now().isoformat(timespec="seconds"),
              "threshold": settings.score_threshold, "top_k": settings.top_k,
              "model": settings.groq_model if args.llm else None, "strategies": {}}
    for strategy in args.strategies:
        print(f"\n######## stratégie : {strategy} ({len(questions)} questions) ########")
        ensure_index(client, embedder, strategy)
        entry = {"retrieval": retrieval_eval(client, embedder, strategy, questions, args.ks)}
        print_retrieval(entry["retrieval"], args.ks)
        if llm:
            entry["llm"] = llm_eval(client, embedder, llm, strategy, questions, args.sleep)
            print_llm(entry["llm"])
        report["strategies"][strategy] = entry

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapport détaillé : {out}")


if __name__ == "__main__":
    main()
