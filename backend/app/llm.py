"""Séance 3 — client du LLM : API Groq (compatible OpenAI). La clé vient du .env, jamais du dépôt."""
import httpx


class LLMUnavailable(Exception):
    """Le LLM ne répond pas ou renvoie une réponse inexploitable -> l'API répond 502."""

def _error_message(response: httpx.Response) -> str:
    """Message d'erreur renvoyé par Groq (ex. « The model `x` does not exist »). Ne contient pas la clé."""
    try:
        return str(response.json()["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        return response.text[:200]

class GroqClient:
    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 60.0, transport=None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport  # injectable pour les tests

    def chat(self, system: str, user: str) -> str:
        if not self.api_key:
            raise LLMUnavailable("GROQ_API_KEY est absente du fichier .env")
        payload = {
            "model": self.model,
            "temperature": 0,  # réponses reproductibles
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as http:
                r = http.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            if r.status_code == 429:
                raise LLMUnavailable("limite de requêtes Groq atteinte, réessayez dans un instant")
            if r.status_code in (401, 403):
                raise LLMUnavailable("clé Groq refusée (vérifiez GROQ_API_KEY)")
            if r.status_code >= 400:
                raise LLMUnavailable(f"Groq a répondu {r.status_code} : {_error_message(r)}")
            return r.json()["choices"][0]["message"]["content"].strip()
        except LLMUnavailable:
            raise
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc