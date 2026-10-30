"""Séance 2 — embeddings. Le modèle e5 exige un préfixe : « passage: » pour les documents
indexés, « query: » pour les questions. Sans eux, la qualité de recherche baisse."""


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None  # chargé au premier usage (le chargement prend quelques secondes)

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(["passage: " + t for t in texts], normalize_embeddings=True,
                                    batch_size=32)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode("query: " + text, normalize_embeddings=True).tolist()