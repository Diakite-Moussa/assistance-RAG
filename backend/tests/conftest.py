import re
import unicodedata
import zlib
from math import sqrt

import chromadb
import pytest


class FakeEmbedder:
    """Embedder déterministe pour les tests : sac de mots haché, normalisé.
    Évite de télécharger le vrai modèle ; deux textes qui partagent des mots sont proches."""

    DIM = 512

    def _vec(self, text: str) -> list[float]:
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
        v = [0.0] * self.DIM
        for w in re.findall(r"[a-z0-9]+", text):
            if len(w) > 2:
                v[zlib.crc32(w.encode()) % self.DIM] += 1.0
        norm = sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_passages(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture()
def embedder():
    return FakeEmbedder()


@pytest.fixture()
def client(tmp_path):
    return chromadb.PersistentClient(path=str(tmp_path / "chroma"))

@pytest.fixture()
def indexed(client, embedder):
    from app import indexing

    indexing.ingest(client, embedder, "structural", 500, 100, 900)
    return client    