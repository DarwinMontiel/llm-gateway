"""Proveedor en la nube: Groq (API compatible con OpenAI). Streaming por Server-Sent Events."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Self

import httpx

from puente_llm.errors import AuthenticationError
from puente_llm.providers.base import raise_for_status, translate_transport_errors
from puente_llm.types import Completion, Message


def iter_sse_text(lines: Iterable[str]) -> Iterator[str]:
    """Extrae ``choices[0].delta.content`` de un stream SSE estilo OpenAI (termina en [DONE])."""
    for line in lines:
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            return
        chunk: dict[str, Any] = json.loads(data)
        delta = chunk["choices"][0].get("delta", {})
        if text := delta.get("content"):
            yield text


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.groq.com/openai/v1",
        default_model: str = "llama-3.1-8b-instant",
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.default_model = default_model
        self._api_key = api_key or None
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    @property
    def configured(self) -> bool:
        """``True`` si hay una clave; sin ella el proveedor existe pero no puede responder."""
        return self._api_key is not None

    def _headers(self) -> dict[str, str]:
        # La clave se valida al usarla (no al construir) para que una cadena "local primero"
        # funcione aunque la nube no esté configurada.
        if self._api_key is None:
            raise AuthenticationError(
                self.name, "falta GROQ_API_KEY (defínela en el entorno o en .env)"
            )
        return {"Authorization": f"Bearer {self._api_key}"}

    def close(self) -> None:
        """Cierra el cliente HTTP si lo creó este proveedor (uno inyectado lo cierra su dueño)."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _payload(
        self, messages: Sequence[Message], model: str | None, temperature: float, stream: bool
    ) -> dict[str, Any]:
        return {
            "model": model or self.default_model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

    def complete(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Completion:
        headers = self._headers()
        payload = self._payload(messages, model, temperature, stream=False)
        started = time.perf_counter()
        try:
            response = self._client.post("/chat/completions", json=payload, headers=headers)
        except httpx.HTTPError as error:
            raise translate_transport_errors(self.name, error) from error
        raise_for_status(self.name, response)
        data = response.json()
        usage = data.get("usage", {})
        return Completion(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", payload["model"]),
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

    def stream(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Iterator[str]:
        headers = self._headers()
        payload = self._payload(messages, model, temperature, stream=True)
        try:
            with self._client.stream(
                "POST", "/chat/completions", json=payload, headers=headers
            ) as response:
                if not response.is_success:
                    response.read()
                raise_for_status(self.name, response)
                yield from iter_sse_text(response.iter_lines())
        except httpx.HTTPError as error:
            raise translate_transport_errors(self.name, error) from error
