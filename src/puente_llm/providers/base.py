from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Protocol

import httpx

from puente_llm.errors import (
    AuthenticationError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitedError,
)
from puente_llm.types import Completion, Message


class Provider(Protocol):
    name: str

    def complete(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Completion: ...

    def stream(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Iterator[str]: ...


def raise_for_status(provider: str, response: httpx.Response) -> None:
    """Traduce códigos HTTP a la jerarquía de errores del gateway."""
    if response.is_success:
        return
    status = response.status_code
    if status in (401, 403):
        raise AuthenticationError(provider, f"credencial rechazada (HTTP {status})")
    if status == 429:
        retry_after = response.headers.get("retry-after")
        raise RateLimitedError(
            provider, "límite de solicitudes", float(retry_after) if retry_after else None
        )
    if status >= 500:
        raise ProviderUnavailableError(provider, f"error del servidor (HTTP {status})")
    raise ProviderError(provider, f"HTTP {status}: {response.text[:200]}")


def translate_transport_errors(provider: str, error: httpx.HTTPError) -> ProviderError:
    if isinstance(error, httpx.TimeoutException):
        return ProviderUnavailableError(provider, "tiempo de espera agotado")
    if isinstance(error, httpx.TransportError):
        return ProviderUnavailableError(provider, f"no se pudo conectar ({type(error).__name__})")
    return ProviderError(provider, str(error))
