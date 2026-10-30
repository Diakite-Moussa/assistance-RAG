import json

import httpx
import pytest

from app.llm import GroqClient, LLMUnavailable


def _client(handler, key="gsk_test"):
    return GroqClient(key, "llama-3.3-70b-versatile", "https://api.example.test/openai/v1",
                      transport=httpx.MockTransport(handler))


def test_groq_client_sends_openai_format_and_parses_answer():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": " 18 semaines [1]. "}}]})

    answer = _client(handler).chat("système", "utilisateur")
    assert answer == "18 semaines [1]."
    assert seen["url"].endswith("/chat/completions")
    assert seen["auth"] == "Bearer gsk_test"
    assert seen["body"]["temperature"] == 0
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


@pytest.mark.parametrize("status", [429, 401, 500])
def test_groq_errors_become_llm_unavailable(status):
    with pytest.raises(LLMUnavailable):
        _client(lambda request: httpx.Response(status, json={"error": "x"})).chat("s", "u")


def test_missing_api_key_is_reported_without_network_call():
    def never(request):
        raise AssertionError("aucun appel réseau attendu")

    with pytest.raises(LLMUnavailable, match="GROQ_API_KEY"):
        _client(never, key="").chat("s", "u")


def test_error_message_never_contains_the_api_key():
    with pytest.raises(LLMUnavailable) as err:
        _client(lambda request: httpx.Response(401, json={})).chat("s", "u")
    assert "gsk_test" not in str(err.value)

def test_groq_error_message_is_surfaced_for_diagnosis():
    body = {"error": {"message": "The model `llama-9000` does not exist", "code": "model_not_found"}}
    with pytest.raises(LLMUnavailable) as err:
        _client(lambda request: httpx.Response(404, json=body)).chat("s", "u")
    assert "404" in str(err.value) and "llama-9000" in str(err.value)    