from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import rag
from app.config import settings
from app.llm import LLMUnavailable
from app.main import app, get_client, get_embedder, get_llm
from app.prompt import REFUSAL


class FakeLLM:
    """LLM factice : renvoie une réponse prévue et garde en mémoire ce qu'on lui a envoyé."""

    def __init__(self, reply="Réponse test [1]."):
        self.reply, self.calls, self.last_user = reply, 0, ""

    def chat(self, system, user):
        self.calls += 1
        self.last_user = user
        return self.reply


LOW = 0.05  # seuil bas pour les tests : le faux embedder donne des scores plus faibles que e5


def _ask(client, embedder, llm, question="durée minimale du PFE", threshold=LOW):
    return rag.ask(client, embedder, llm, question, 5, "structural", None, threshold)


def test_out_of_corpus_question_is_refused_without_calling_llm(indexed, embedder):
    llm = FakeLLM()
    res = _ask(indexed, embedder, llm, question="zzzz qqqq wwww", threshold=0.30)
    assert res["found"] is False
    assert res["answer"] == REFUSAL
    assert res["sources"] == []
    assert llm.calls == 0  # le seuil a refusé AVANT d'appeler le modèle


def test_llm_refusal_is_normalized_to_exact_sentence(indexed, embedder):
    llm = FakeLLM("Désolé. Je ne trouve pas cette information dans les documents de l’École. Bonne journée")
    res = _ask(indexed, embedder, llm)
    assert res["found"] is False and res["answer"] == REFUSAL and res["sources"] == []


def test_invalid_citations_are_reported(indexed, embedder):
    llm = FakeLLM("La durée est de 18 semaines [1], voir aussi [2, 42] et [99].")
    res = _ask(indexed, embedder, llm)
    assert res["found"] is True
    assert res["invalid_citations"] == [42, 99]
    assert [s["id"] for s in res["sources"]] == list(range(1, len(res["sources"]) + 1))


def test_answer_without_valid_citation_is_treated_as_refusal(indexed, embedder):
    # cas réel observé avec Llama : refus reformulé, sans citation -> ne doit pas passer pour « trouvé »
    llm = FakeLLM("Je ne peux pas répondre à cette question car elle n'est pas liée aux documents.")
    res = _ask(indexed, embedder, llm)
    assert res["found"] is False and res["answer"] == REFUSAL and res["sources"] == []
    # une citation qui ne pointe vers aucun fragment ne suffit pas non plus
    res = _ask(indexed, embedder, FakeLLM("C'est 18 semaines [99]."))
    assert res["found"] is False


def test_extract_citations():
    assert rag.extract_citations("a [1] b [2, 3] c [1] d [x]") == [1, 2, 3]
    assert rag.extract_citations("aucune citation") == []


def test_amending_document_is_added_to_the_context(indexed, embedder):
    llm = FakeLLM("ok [1]")
    # question centrée sur le guide : le document modificatif doit être ajouté automatiquement
    _ask(indexed, embedder, llm, question="Quelle est la durée du PFE entre 16 et 24 semaines ? Guide des stages")
    assert "EIH-SRE-GUIDE-2026" in llm.last_user
    assert "CE DOCUMENT MODIFIE EIH-SRE-GUIDE-2026" in llm.last_user  # fragment de la note 2026-14


def test_prompt_shows_reference_date_and_status(indexed, embedder):
    llm = FakeLLM("ok [1]")
    _ask(indexed, embedder, llm)
    assert "réf. " in llm.last_user and "publié le 20" in llm.last_user and "statut :" in llm.last_user


@pytest.fixture()
def api(indexed, embedder, monkeypatch):
    monkeypatch.setattr("app.main.settings", replace(settings, score_threshold=LOW))
    app.dependency_overrides[get_client] = lambda: indexed
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_llm] = lambda: FakeLLM("18 semaines [1].")
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_api_ask_returns_the_contract(api):
    r = api.post("/api/ask", json={"question": "durée minimale du PFE", "top_k": 5, "filters": {"type": None}})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "found", "sources", "invalid_citations", "latency_ms"}
    assert body["found"] is True
    assert {"id", "chunk_id", "file", "reference", "date", "page", "section", "excerpt", "score"} <= set(body["sources"][0])


def test_api_ask_empty_question_gives_422(api):
    assert api.post("/api/ask", json={"question": "  "}).status_code == 422


def test_api_ask_gives_502_when_llm_is_down(api):
    class Down:
        def chat(self, system, user):
            raise LLMUnavailable("connexion refusée")

    app.dependency_overrides[get_llm] = lambda: Down()
    r = api.post("/api/ask", json={"question": "durée minimale du PFE"})
    assert r.status_code == 502
