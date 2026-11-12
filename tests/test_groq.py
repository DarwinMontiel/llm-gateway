from __future__ import annotations

import json

import httpx
import pytest

from puente_llm import AuthenticationError, Message, RateLimitedError
from puente_llm.providers.groq import GroqProvider, iter_sse_text


def test_missing_api_key_fails_on_use_without_calling_the_api(make_client) -> None:  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no debe salir a la red sin clave")

    provider = GroqProvider(api_key=None, client=make_client(handler))
    assert provider.configured is False
    with pytest.raises(AuthenticationError, match="GROQ_API_KEY"):
        provider.complete([Message.user("hola")])
    with pytest.raises(AuthenticationError, match="GROQ_API_KEY"):
        list(provider.stream([Message.user("hola")]))


def test_close_only_closes_its_own_client(make_client) -> None:  # type: ignore[no-untyped-def]
    injected = make_client(lambda _: httpx.Response(200))
    with GroqProvider("k", client=injected):
        pass
    assert not injected.is_closed  # el cliente inyectado lo cierra quien lo creó

    with GroqProvider("k") as own:
        pass
    assert own._client.is_closed


def test_complete_sends_bearer_and_parses_openai_format(make_client) -> None:  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.url.path.endswith("/chat/completions")
        body = json.loads(request.content)
        assert body["model"] == "llama-3.1-8b-instant"
        return httpx.Response(
            200,
            json={
                "model": "llama-3.1-8b-instant",
                "choices": [
                    {"message": {"role": "assistant", "content": "Dispersión de Rayleigh."}}
                ],
                "usage": {"prompt_tokens": 15, "completion_tokens": 6},
            },
        )

    provider = GroqProvider("test-key", client=make_client(handler))
    result = provider.complete([Message.user("¿Por qué el cielo es azul?")])

    assert result.text == "Dispersión de Rayleigh."
    assert (result.prompt_tokens, result.completion_tokens) == (15, 6)


def test_stream_parses_server_sent_events(make_client) -> None:  # type: ignore[no-untyped-def]
    events = [
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',
        'data: {"choices":[{"delta":{"content":"El cielo"}}]}',
        "",
        'data: {"choices":[{"delta":{"content":" es azul"}}]}',
        "data: [DONE]",
    ]
    body = "\n".join(events).encode()
    provider = GroqProvider("k", client=make_client(lambda _: httpx.Response(200, content=body)))

    assert "".join(provider.stream([Message.user("hola")])) == "El cielo es azul"


def test_sse_parser_ignores_comments_and_stops_at_done() -> None:
    lines = [
        ": keep-alive",
        'data: {"choices":[{"delta":{"content":"a"}}]}',
        "data: [DONE]",
        "data: x",
    ]
    assert list(iter_sse_text(lines)) == ["a"]


@pytest.mark.parametrize(("status", "error"), [(401, AuthenticationError), (429, RateLimitedError)])
def test_http_errors_are_translated(make_client, status, error) -> None:  # type: ignore[no-untyped-def]
    headers = {"retry-after": "3"} if status == 429 else {}
    provider = GroqProvider(
        "k", client=make_client(lambda _: httpx.Response(status, headers=headers))
    )
    with pytest.raises(error) as info:
        provider.complete([Message.user("hola")])
    if status == 429:
        assert info.value.retry_after == 3.0
