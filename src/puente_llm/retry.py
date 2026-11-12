"""Reintentos con backoff exponencial para errores transitorios."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from puente_llm.errors import ProviderUnavailableError, RateLimitedError

T = TypeVar("T")

logger = logging.getLogger(__name__)


def with_retries(
    call: Callable[[], T],
    attempts: int = 3,
    base_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
    max_wait: float = 30.0,
) -> T:
    """Reintenta errores transitorios con backoff exponencial (0.5 s, 1 s, 2 s…).

    En HTTP 429 respeta ``Retry-After`` si el proveedor lo envía. Si la espera pedida supera
    ``max_wait`` segundos, no se espera: el error se propaga para que el gateway pase al
    siguiente proveedor en lugar de bloquear el proceso. Los errores de autenticación u otros
    no transitorios se propagan de inmediato.
    """
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except (ProviderUnavailableError, RateLimitedError) as error:
            if attempt == attempts:
                raise
            delay = base_delay * 2 ** (attempt - 1)
            if isinstance(error, RateLimitedError) and error.retry_after:
                if error.retry_after > max_wait:
                    logger.warning(
                        "%s; pide esperar %.0f s (máximo %.0f s), no se reintenta",
                        error,
                        error.retry_after,
                        max_wait,
                    )
                    raise
                delay = max(delay, error.retry_after)
            logger.warning("%s; intento %d de %d en %.1f s", error, attempt + 1, attempts, delay)
            sleep(delay)
    raise AssertionError("inalcanzable")  # pragma: no cover
