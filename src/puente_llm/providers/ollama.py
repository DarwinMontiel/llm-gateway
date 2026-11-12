"""Proveedor local: Ollama (https://ollama.com). API: POST /api/chat, streaming en NDJSON."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Iterator, Sequence
from typing import Any

import httpx

from puente_llm.errors import ProviderError
from puente_llm.providers.base import raise_for_status, translate_transport_errors
from puente_llm.types import Completion, Message


def iter_ndjson_text(lines: Iterable[str]) -> Iterator[str]:
    """Extrae el texto de un stream NDJSON de Ollama.

    Soporta ``/api/chat`` (``message.content``) y ``/api/generate`` (``response``); termina en
    la línea con ``"done": true``.
    """
    for line in lines:
        if not line.strip():
            continue
        chunk: dict[str, Any] = json.loads(line)
        if "error" in chunk:
            raise ProviderError("ollama", str(chunk["error"]))
        text = chunk.get("message", {}).get("content") or chunk.get("response") or ""
        if text:
            yield text
        if chunk.get("done"):
            return


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2",
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.default_model = default_model
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def _payload(
        self, messages: Sequence[Message], model: str | None, temperature: float, stream: bool
    ) -> dict[str, Any]:
        return {
            "model": model or self.default_model,
            "messages": [m.to_dict() for m in messages],
            "stream": stream,
            "options": {"temperature": temperature},
        }

    def complete(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Completion:
        payload = self._payload(messages, model, temperature, stream=False)
        started = time.perf_counter()
        try:
            response = self._client.post("/api/chat", json=payload)
        except httpx.HTTPError as error:
            raise translate_transport_errors(self.name, error) from error
        raise_for_status(self.name, response)
        data = response.json()
        return Completion(
            text=data["message"]["content"],
            model=data.get("model", payload["model"]),
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )

    def stream(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Iterator[str]:
        payload = self._payload(messages, model, temperature, stream=True)
        try:
            with self._client.stream("POST", "/api/chat", json=payload) as response:
                if not response.is_success:
                    response.read()
                raise_for_status(self.name, response)
                yield from iter_ndjson_text(response.iter_lines())
        except httpx.HTTPError as error:
            raise translate_transport_errors(self.name, error) from error

    def list_models(self) -> list[str]:
        try:
            response = self._client.get("/api/tags")
        except httpx.HTTPError as error:
            raise translate_transport_errors(self.name, error) from error
        raise_for_status(self.name, response)
        return sorted(m["name"] for m in response.json().get("models", []))
