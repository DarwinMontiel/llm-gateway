from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from puente_llm.errors import ProviderUnavailableError, RateLimitedError

T = TypeVar("T")


def with_retries(
    call: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Reintenta errores transitorios con backoff exponencial (0.5 s, 1 s, 2 s…).

    En HTTP 429 respeta ``Retry-After`` si el proveedor lo envía. Los errores de autenticación
    u otros no transitorios se propagan de inmediato.
    """
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except (ProviderUnavailableError, RateLimitedError) as error:
            if attempt == attempts:
                raise
            delay = base_delay * 2 ** (attempt - 1)
            if isinstance(error, RateLimitedError) and error.retry_after:
                delay = max(delay, error.retry_after)
            sleep(delay)
    raise AssertionError("inalcanzable")  # pragma: no cover
