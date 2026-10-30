"""Calibration de SCORE_THRESHOLD à partir de mesures réelles (vrai modèle e5, vraie base Chroma).

Pour chaque question de eval/questions.json, on relève le score du MEILLEUR fragment retrouvé.
Le seuil idéal sépare les deux groupes : il doit être <= au plus bas score « dans le corpus »
et > au plus haut score « hors corpus ».

Usage (depuis la racine du projet, base déjà indexée via POST /api/ingest) :
    uv run python eval/calibrate_threshold.py
    uv run python eval/calibrate_threshold.py --strategy fixed
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import chromadb  # noqa: E402

from app import indexing  # noqa: E402
from app.config import settings  # noqa: E402
from app.embeddings import Embedder  # noqa: E402


def best_score(client, embedder, question: str, strategy: str) -> tuple[float, str]:
    hits = indexing.search(client, embedder, question, 1, strategy)
    if not hits:
        return 0.0, "(aucun résultat)"
    return hits[0]["score"], f"{hits[0]['reference']} — {hits[0]['section'][:50]}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=settings.chunk_strategy, choices=["fixed", "structural"])
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.json"))
    args = ap.parse_args()

    data = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if "questions" in data:  # format du jeu de test complet (eval/questions.json)
        qs = data["questions"]
        data = {
            "in_corpus": [q["question"] for q in qs if q["expect_found"]],
            "out_of_corpus": [q["question"] for q in qs if q["category"] == "out_of_corpus"],
            "same_topic_no_answer": [q["question"] for q in qs if q["category"] == "same_topic_no_answer"],
        }
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    if indexing.get_collection(client, args.strategy).count() == 0:
        sys.exit("Index vide : lancez d'abord POST /api/ingest.")
    embedder = Embedder(settings.embedding_model)

    results = {}
    # same_topic_no_answer est affiché mais exclu du calcul : le seuil ne peut pas le refuser.
    for group in ("in_corpus", "out_of_corpus", "same_topic_no_answer"):
        if group not in data:
            continue
        print(f"\n=== {group} ===")
        scores = []
        for q in data[group]:
            s, where = best_score(client, embedder, q, args.strategy)
            scores.append(s)
            print(f"{s:.4f}  {q[:60]:<60}  -> {where}")
        results[group] = scores

    if "same_topic_no_answer" in results:
        print("\n(same_topic_no_answer : à vérifier avec le LLM via /api/ask, le refus doit venir du prompt.)")

    low_in, high_out = min(results["in_corpus"]), max(results["out_of_corpus"])
    print(f"\nPlus bas score dans le corpus : {low_in:.4f}")
    print(f"Plus haut score hors corpus   : {high_out:.4f}")
    print(f"Seuil actuel (SCORE_THRESHOLD): {settings.score_threshold:.2f}")

    if low_in > high_out:
        suggested = round((low_in + high_out) / 2, 2)
        print(f"-> Séparation nette. Seuil suggéré : {suggested:.2f} (milieu de la marge de {low_in - high_out:.4f}).")
        if not high_out < settings.score_threshold <= low_in:
            print("   ATTENTION : le seuil actuel ne sépare pas les deux groupes, mettez à jour le .env.")
    else:
        print("-> Chevauchement : aucun seuil ne sépare les groupes. Le seuil seul ne suffira pas ;")
        print("   le refus repose alors sur le prompt et les contrôles de citations (étendre le jeu de questions).")


if __name__ == "__main__":
    main()
