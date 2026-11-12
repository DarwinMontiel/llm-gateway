from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
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
        retry_after = parse_retry_after(response.headers.get("retry-after"))
        raise RateLimitedError(provider, "límite de solicitudes", retry_after)
    if status >= 500:
        raise ProviderUnavailableError(provider, f"error del servidor (HTTP {status})")
    raise ProviderError(provider, f"HTTP {status}: {response.text[:200]}")


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Interpreta la cabecera ``Retry-After`` en segundos.

    El estándar HTTP admite dos formatos: un número de segundos (``"3"``) o una fecha HTTP
    (``"Wed, 21 Oct 2026 07:28:00 GMT"``). Un valor ilegible devuelve ``None`` para que el
    reintento use su backoff normal en lugar de romperse.
    """
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return max(seconds, 0.0) if math.isfinite(seconds) else None
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    now = now or datetime.now(UTC)
    return max((moment - now).total_seconds(), 0.0)


def translate_transport_errors(provider: str, error: httpx.HTTPError) -> ProviderError:
    if isinstance(error, httpx.TimeoutException):
        return ProviderUnavailableError(provider, "tiempo de espera agotado")
    if isinstance(error, httpx.TransportError):
        return ProviderUnavailableError(provider, f"no se pudo conectar ({type(error).__name__})")
    return ProviderError(provider, str(error))
