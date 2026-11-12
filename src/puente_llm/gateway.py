"""Gateway: cadena de proveedores con reintentos y respaldo (p. ej. local primero, nube después)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from functools import partial
from typing import Self, TypeVar

from puente_llm.errors import (
    AllProvidersFailedError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitedError,
)
from puente_llm.providers.base import Provider
from puente_llm.retry import with_retries
from puente_llm.types import Completion, Message

FALLBACK_ON = (ProviderUnavailableError, RateLimitedError)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Gateway:
    """Recorre los proveedores en orden: reintenta los fallos transitorios y, si persisten,
    pasa al siguiente. Los errores de credenciales se propagan de inmediato.

    Se puede usar como *context manager* para cerrar las conexiones de los proveedores::

        with build_gateway(["ollama", "groq"]) as gateway:
            gateway.complete("...")
    """

    def __init__(
        self,
        providers: Sequence[Provider],
        attempts: int = 2,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("se requiere al menos un proveedor")
        self.providers = list(providers)
        self._attempts = attempts
        self._sleep = sleep

    def complete(
        self,
        prompt: str | Sequence[Message],
        *,
        system: str | None = None,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> Completion:
        """Responde con el primer proveedor disponible.

        ``model`` solo se aplica al primer proveedor (cada uno tiene su catálogo); los de
        respaldo usan su modelo por defecto.
        """
        messages = self._messages(prompt, system)
        errors: list[ProviderError] = []
        for index, provider in enumerate(self.providers):
            chosen = model if index == 0 else None
            call = partial(provider.complete, messages, model=chosen, temperature=temperature)
            try:
                return self._retry(call)
            except FALLBACK_ON as error:
                errors.append(error)
                self._log_fallback(index, error)
        raise AllProvidersFailedError(errors)

    def stream(
        self,
        prompt: str | Sequence[Message],
        *,
        system: str | None = None,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> Iterator[str]:
        """Streaming con la misma política de reintentos y respaldo que :meth:`complete`.

        Se reintenta y se cambia de proveedor solo **antes** del primer fragmento: una vez que
        empieza a llegar texto, un fallo se propaga para no mezclar dos respuestas distintas.
        """
        messages = self._messages(prompt, system)
        errors: list[ProviderError] = []
        for index, provider in enumerate(self.providers):
            chosen = model if index == 0 else None
            opener = partial(_open_stream, provider, messages, chosen, temperature)
            try:
                first, chunks = self._retry(opener)
            except FALLBACK_ON as error:
                errors.append(error)
                self._log_fallback(index, error)
                continue
            if first is None:
                return
            yield first
            yield from chunks
            return
        raise AllProvidersFailedError(errors)

    def close(self) -> None:
        """Cierra los clientes HTTP de los proveedores que lo permitan."""
        for provider in self.providers:
            close = getattr(provider, "close", None)
            if callable(close):
                close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _retry(self, call: Callable[[], T]) -> T:
        if self._sleep is None:
            return with_retries(call, attempts=self._attempts)
        return with_retries(call, attempts=self._attempts, sleep=self._sleep)

    def _log_fallback(self, index: int, error: ProviderError) -> None:
        if index + 1 < len(self.providers):
            logger.warning("%s; paso a %s", error, self.providers[index + 1].name)

    @staticmethod
    def _messages(prompt: str | Sequence[Message], system: str | None) -> list[Message]:
        messages = [Message.user(prompt)] if isinstance(prompt, str) else list(prompt)
        if system:
            messages.insert(0, Message.system(system))
        return messages


def _open_stream(
    provider: Provider, messages: list[Message], model: str | None, temperature: float
) -> tuple[str | None, Iterator[str]]:
    """Abre un stream y espera el primer fragmento; así los fallos de conexión ocurren aquí,
    dentro del bucle de reintentos, y no a mitad de la respuesta."""
    chunks = provider.stream(messages, model=model, temperature=temperature)
    try:
        return next(chunks), chunks
    except StopIteration:
        return None, iter(())
