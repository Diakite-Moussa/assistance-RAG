import pytest
from fastapi.testclient import TestClient

from app.main import app, get_client, get_embedder


@pytest.fixture()
def api(client, embedder):
    app.dependency_overrides[get_client] = lambda: client
    app.dependency_overrides[get_embedder] = lambda: embedder
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_ok(api):
    r = api.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_health_503_when_database_unavailable():
    class Broken:
        def get_or_create_collection(self, **kw):
            raise RuntimeError("down")

    app.dependency_overrides[get_client] = lambda: Broken()
    try:
        assert TestClient(app).get("/api/health").status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_ingest_then_documents_and_search(api):
    r = api.post("/api/ingest", json={"strategy": "structural", "chunk_size": 500, "chunk_overlap": 100})
    assert r.status_code == 200 and r.json()["chunks"] > 50
    assert len(api.get("/api/documents").json()) == 7
    hits = api.post("/api/search", json={"question": "durée minimale du PFE", "top_k": 3}).json()["hits"]
    assert len(hits) == 3 and hits[0]["score"] >= hits[-1]["score"]


def test_ingest_invalid_parameters_give_422(api):
    assert api.post("/api/ingest", json={"chunk_size": 200, "chunk_overlap": 300}).status_code == 422
    assert api.post("/api/ingest", json={"strategy": "magic"}).status_code == 422


@pytest.mark.parametrize("question", ["", "   "])
def test_search_empty_question_gives_422(api, question):
    assert api.post("/api/search", json={"question": question}).status_code == 422