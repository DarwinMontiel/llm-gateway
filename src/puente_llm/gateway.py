"""Gateway: cadena de proveedores con reintentos y fallback (p. ej. local primero, nube después)."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from functools import partial

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


class Gateway:
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
        raise AllProvidersFailedError(errors)

    def stream(
        self,
        prompt: str | Sequence[Message],
        *,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        """Streaming con fallback solo si el proveedor falla antes de emitir el primer fragmento."""
        messages = self._messages(prompt, system)
        errors: list[ProviderError] = []
        for provider in self.providers:
            chunks = provider.stream(messages, temperature=temperature)
            try:
                first = next(chunks)
            except StopIteration:
                return
            except FALLBACK_ON as error:
                errors.append(error)
                continue
            yield first
            yield from chunks
            return
        raise AllProvidersFailedError(errors)

    def _retry(self, call: Callable[[], Completion]) -> Completion:
        if self._sleep is None:
            return with_retries(call, attempts=self._attempts)
        return with_retries(call, attempts=self._attempts, sleep=self._sleep)

    @staticmethod
    def _messages(prompt: str | Sequence[Message], system: str | None) -> list[Message]:
        messages = [Message.user(prompt)] if isinstance(prompt, str) else list(prompt)
        if system:
            messages.insert(0, Message.system(system))
        return messages
