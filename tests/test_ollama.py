from __future__ import annotations

import json

import httpx
import pytest

from puente_llm import Message, ProviderUnavailableError
from puente_llm.errors import ProviderError
from puente_llm.providers.ollama import OllamaProvider, iter_ndjson_text


def test_complete_parses_chat_response_and_tokens(make_client) -> None:  # type: ignore[no-untyped-def]
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "model": "llama3.2",
                "message": {"role": "assistant", "content": "Por la dispersión de Rayleigh."},
                "prompt_eval_count": 12,
                "eval_count": 9,
            },
        )

    provider = OllamaProvider(client=make_client(handler))
    result = provider.complete([Message.user("¿Por qué el cielo es azul?")], temperature=0.1)

    assert result.text == "Por la dispersión de Rayleigh."
    assert (result.provider, result.prompt_tokens, result.completion_tokens) == ("ollama", 12, 9)
    assert seen["stream"] is False
    assert seen["options"] == {"temperature": 0.1}
    assert seen["messages"] == [{"role": "user", "content": "¿Por qué el cielo es azul?"}]


def test_stream_parses_real_ndjson_capture(make_client, ollama_stream_body) -> None:  # type: ignore[no-untyped-def]
    """La captura proviene de una ejecución real de tinyllama contra /api/generate."""
    provider = OllamaProvider(
        client=make_client(lambda _: httpx.Response(200, content=ollama_stream_body))
    )

    text = "".join(provider.stream([Message.user("¿Por qué el cielo es azul?")]))

    expected = "".join(
        json.loads(line).get("response", "") for line in ollama_stream_body.splitlines()
    )
    assert text == expected
    assert text.startswith("The sky blue color occurs")


def test_ndjson_parser_supports_chat_format_and_stops_at_done() -> None:
    lines = [
        json.dumps({"message": {"content": "Hola"}, "done": False}),
        "",
        json.dumps({"message": {"content": " mundo"}, "done": True}),
        json.dumps({"message": {"content": "ignorado"}, "done": False}),
    ]
    assert "".join(iter_ndjson_text(lines)) == "Hola mundo"


def test_ndjson_error_line_raises() -> None:
    with pytest.raises(ProviderError, match="model not found"):
        list(iter_ndjson_text([json.dumps({"error": "model not found"})]))


def test_connection_refused_is_unavailable(make_client) -> None:  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    provider = OllamaProvider(client=make_client(handler))
    with pytest.raises(ProviderUnavailableError, match="no se pudo conectar"):
        provider.complete([Message.user("hola")])


def test_server_error_is_unavailable_and_list_models(make_client) -> None:  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "tinyllama"}, {"name": "llama3.2"}]}
            )
        return httpx.Response(503)

    provider = OllamaProvider(client=make_client(handler))
    assert provider.list_models() == ["llama3.2", "tinyllama"]
    with pytest.raises(ProviderUnavailableError, match="503"):
        list(provider.stream([Message.user("hola")]))


def test_close_only_closes_its_own_client(make_client) -> None:  # type: ignore[no-untyped-def]
    injected = make_client(lambda _: httpx.Response(200))
    OllamaProvider(client=injected).close()
    assert not injected.is_closed

    with OllamaProvider() as own:
        pass
    assert own._client.is_closed
