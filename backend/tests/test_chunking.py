import pytest

from app.chunking import chunk_corpus, chunk_fixed
from app.config import settings
from app.extract import extract_corpus, parse_french_date


@pytest.fixture(scope="module")
def docs():
    return extract_corpus(settings.corpus_dir)


@pytest.fixture(scope="module")
def structural(docs):
    return chunk_corpus(docs, "structural", max_chars=900)


def test_parse_french_date():
    assert parse_french_date("1er septembre 2026") == "2026-09-01"
    assert parse_french_date("10 juillet 2026") == "2026-07-10"
    assert parse_french_date("n'importe quoi") == ""


def test_metadata_complete_on_every_chunk(structural):
    for c in structural:
        for key in ("reference", "type", "date", "version", "status", "page", "section"):
            assert c[key] not in ("", None), f"{key} manquant dans {c['id']}"


def test_amending_note_is_detected_generically(docs):
    by_ref = {d["meta"]["reference"]: d["meta"] for d in docs}
    note = next(m for r, m in by_ref.items() if "NS" in r)
    assert note["amends"] == "EIH-SRE-GUIDE-2026"
    assert all(m["amends"] == "" for r, m in by_ref.items() if "NS" not in r)


def test_header_footer_and_artifacts_removed(structural):
    for c in structural:
        assert "établissement fictif" not in c["content"]
        assert "Document fictif" not in c["content"]
        assert "(cid:" not in c["content"]


def test_table_row_keeps_its_headers_and_its_section(structural):
    chunk = next(c for c in structural if "Article 3 " in c["section"])
    assert "Année : 2A — Semestres : S3, S4" in chunk["content"]
    cal = [c for c in structural if "Date limite d'inscription au rattrapage des modules S1, S3, S5" in c["content"]]
    assert cal and cal[0]["section"].startswith("2. Semestres impairs")


def test_structural_has_no_title_only_chunk(structural):
    assert all(len(c["content"]) > 40 for c in structural)
    assert all(len(c["content"]) <= 900 + 150 for c in structural)


def test_fixed_chunking_respects_size_and_overlap(docs):
    chunks = chunk_fixed(docs[0], size=500, overlap=100)
    assert len(chunks) > 3
    assert all(len(c["content"]) <= 500 for c in chunks)
    # chevauchement : la fin d'un fragment réapparaît au début du suivant
    assert chunks[0]["content"][-30:].split()[-1] in chunks[1]["content"]


def test_fixed_chunking_rejects_bad_parameters(docs):
    with pytest.raises(ValueError):
        chunk_fixed(docs[0], size=100, overlap=100)


def test_chunk_ids_are_unique_and_stable(docs):
    a = chunk_corpus(docs, "structural")
    b = chunk_corpus(docs, "structural")
    assert [c["id"] for c in a] == [c["id"] for c in b]
    assert len({c["id"] for c in a}) == len(a)