from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest

from puente_llm import (
    AllProvidersFailedError,
    AuthenticationError,
    Completion,
    Gateway,
    Message,
    ProviderUnavailableError,
    RateLimitedError,
)
from puente_llm.retry import with_retries


class FakeProvider:
    def __init__(
        self, name: str, failures: list[Exception] | None = None, chunks: list[str] | None = None
    ) -> None:
        self.name = name
        self.failures = list(failures or [])
        self.chunks = ["hola", " mundo"] if chunks is None else chunks
        self.calls: list[tuple[list[Message], str | None]] = []
        self.stream_models: list[str | None] = []
        self.closed = False

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
        self.stream_models.append(model)
        if self.failures:
            raise self.failures.pop(0)
        yield from self.chunks

    def close(self) -> None:
        self.closed = True


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
    local = FakeProvider("local", failures=[unavailable(), unavailable()])
    cloud = FakeProvider("cloud", chunks=["desde", " la nube"])
    gateway = Gateway([local, cloud], attempts=2, sleep=lambda _: None)
    assert "".join(gateway.stream("hola")) == "desde la nube"


def test_stream_retries_the_same_provider_before_falling_back() -> None:
    sleeps: list[float] = []
    local = FakeProvider("local", failures=[unavailable()], chunks=["promesa", " de pago"])
    cloud = FakeProvider("cloud")
    text = "".join(Gateway([local, cloud], attempts=2, sleep=sleeps.append).stream("hola"))

    assert text == "promesa de pago"
    assert sleeps == [0.5]
    assert cloud.stream_models == []  # el respaldo no se usó


def test_stream_applies_model_only_to_first_provider() -> None:
    local = FakeProvider("local", failures=[unavailable(), unavailable()])
    cloud = FakeProvider("cloud", chunks=["ok"])
    gateway = Gateway([local, cloud], attempts=2, sleep=lambda _: None)

    assert "".join(gateway.stream("hola", model="llama3.2")) == "ok"
    assert local.stream_models == ["llama3.2", "llama3.2"]
    assert cloud.stream_models == [None]


def test_stream_all_failing_and_empty_stream() -> None:
    local = FakeProvider("local", failures=[unavailable("local")] * 2)
    with pytest.raises(AllProvidersFailedError):
        list(Gateway([local], attempts=2, sleep=lambda _: None).stream("hola"))

    assert list(Gateway([FakeProvider("vacío", chunks=[])]).stream("hola")) == []


def test_stream_error_after_first_chunk_is_not_hidden() -> None:
    class Interrupted(FakeProvider):
        def stream(
            self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
        ) -> Iterator[str]:
            yield "Resumen:"
            raise unavailable(self.name)

    cloud = FakeProvider("cloud")
    chunks = Gateway([Interrupted("local"), cloud]).stream("hola")
    assert next(chunks) == "Resumen:"
    with pytest.raises(ProviderUnavailableError):
        next(chunks)
    assert cloud.stream_models == []  # nunca se mezclan dos respuestas


def test_gateway_closes_providers_as_context_manager() -> None:
    local, cloud = FakeProvider("local"), FakeProvider("cloud")
    with Gateway([local, cloud]) as gateway:
        gateway.complete("hola")
    assert local.closed
    assert cloud.closed


def test_fallback_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    local = FakeProvider("local", failures=[unavailable("local")] * 2)
    Gateway([local, FakeProvider("cloud")], attempts=2, sleep=lambda _: None).complete("hola")
    assert "intento 2 de 2" in caplog.text
    assert "paso a cloud" in caplog.text


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
