from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest

from llm_gateway import (
    AllProvidersFailedError,
    AuthenticationError,
    Completion,
    Gateway,
    Message,
    ProviderUnavailableError,
    RateLimitedError,
)
from llm_gateway.retry import with_retries


class FakeProvider:
    def __init__(
        self, name: str, failures: list[Exception] | None = None, chunks: list[str] | None = None
    ) -> None:
        self.name = name
        self.failures = list(failures or [])
        self.chunks = chunks or ["hola", " mundo"]
        self.calls: list[tuple[list[Message], str | None]] = []

    def complete(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Completion:
        self.calls.append((list(messages), model))
        if self.failures:
            raise self.failures.pop(0)
        return Completion(
            text=f"respuesta de {self.name}",
            model=model or "default",
            provider=self.name,
            latency_ms=10,
        )

    def stream(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Iterator[str]:
        if self.failures:
            raise self.failures.pop(0)
        yield from self.chunks


def unavailable(name: str = "local") -> ProviderUnavailableError:
    return ProviderUnavailableError(name, "caído")


def test_uses_first_provider_when_available() -> None:
    local, cloud = FakeProvider("local"), FakeProvider("cloud")
    result = Gateway([local, cloud]).complete("hola", system="Responde breve", model="tinyllama")

    assert result.provider == "local"
    messages, model = local.calls[0]
    assert [m.role for m in messages] == ["system", "user"]
    assert model == "tinyllama"
    assert cloud.calls == []


def test_retries_transient_errors_before_falling_back() -> None:
    sleeps: list[float] = []
    local = FakeProvider("local", failures=[unavailable()])
    result = Gateway([local], attempts=2, sleep=sleeps.append).complete("hola")

    assert result.provider == "local"
    assert len(local.calls) == 2
    assert sleeps == [0.5]


def test_falls_back_to_cloud_with_its_default_model() -> None:
    local = FakeProvider("local", failures=[unavailable(), unavailable()])
    cloud = FakeProvider("cloud")
    result = Gateway([local, cloud], attempts=2, sleep=lambda _: None).complete(
        "hola", model="tinyllama"
    )

    assert result.provider == "cloud"
    assert cloud.calls[0][1] is None  # el modelo pedido era del proveedor local


def test_authentication_errors_do_not_fall_back() -> None:
    local = FakeProvider("local", failures=[AuthenticationError("local", "sin clave")])
    with pytest.raises(AuthenticationError):
        Gateway([local, FakeProvider("cloud")]).complete("hola")


def test_all_providers_failing_reports_every_error() -> None:
    local = FakeProvider("local", failures=[unavailable("local")] * 2)
    cloud = FakeProvider("cloud", failures=[RateLimitedError("cloud", "429")] * 2)
    with pytest.raises(AllProvidersFailedError) as info:
        Gateway([local, cloud], attempts=2, sleep=lambda _: None).complete("hola")
    assert [e.provider for e in info.value.errors] == ["local", "cloud"]


def test_stream_falls_back_only_before_first_chunk() -> None:
    local = FakeProvider("local", failures=[unavailable()])
    cloud = FakeProvider("cloud", chunks=["desde", " la nube"])
    assert "".join(Gateway([local, cloud]).stream("hola")) == "desde la nube"


def test_with_retries_respects_retry_after() -> None:
    sleeps: list[float] = []
    calls = iter([RateLimitedError("x", "429", retry_after=4.0), "ok"])

    def call() -> str:
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    assert with_retries(call, attempts=2, sleep=sleeps.append) == "ok"
    assert sleeps == [4.0]


def test_gateway_requires_providers() -> None:
    with pytest.raises(ValueError, match="al menos un proveedor"):
        Gateway([])


def test_tokens_per_second() -> None:
    completion = Completion(
        text="x", model="m", provider="p", latency_ms=2000, completion_tokens=50
    )
    assert completion.tokens_per_second == 25.0
    assert Completion(text="x", model="m", provider="p", latency_ms=0).tokens_per_second is None
