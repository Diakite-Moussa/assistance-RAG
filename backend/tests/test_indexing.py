from app import indexing


def _ingest(client, embedder, strategy="structural"):
    return indexing.ingest(client, embedder, strategy, 500, 100, 900)


def test_ingest_is_idempotent(client, embedder):
    first = _ingest(client, embedder)
    second = _ingest(client, embedder)
    assert first["total_in_index"] == second["total_in_index"] == first["chunks"]
    assert second["removed"] == 0


def test_ingest_removes_stale_chunks(client, embedder):
    indexing.ingest(client, embedder, "fixed", 300, 50, 900)
    after = indexing.ingest(client, embedder, "fixed", 800, 100, 900)
    assert after["total_in_index"] == after["chunks"]  # pas de fragments orphelins


def test_search_returns_top_k_sorted_with_scores(client, embedder):
    _ingest(client, embedder)
    hits = indexing.search(client, embedder, "date limite inscription rattrapage", 5, "structural")
    assert len(hits) == 5
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 1 for s in scores)
    assert "rattrapage" in hits[0]["content"].lower()


def test_search_filter_by_document_type(client, embedder):
    _ingest(client, embedder)
    hits = indexing.search(client, embedder, "durée du stage", 8, "structural", doc_type="FAQ (questions-réponses)")
    assert hits and all(h["type"] == "FAQ (questions-réponses)" for h in hits)


def test_search_on_empty_index_returns_nothing(client, embedder):
    assert indexing.search(client, embedder, "bonjour", 5, "structural") == []


def test_list_documents_has_all_seven(client, embedder):
    _ingest(client, embedder)
    docs = indexing.list_documents(client, "structural")
    assert len(docs) == 7
    assert sum(d["chunks"] for d in docs) == client.get_collection("eih_scolarite_structural").count()