from __future__ import annotations

from collections.abc import Iterator, Sequence

import pytest
from typer.testing import CliRunner

from puente_llm import (
    AuthenticationError,
    Completion,
    Gateway,
    Message,
    ProviderUnavailableError,
    cli,
)

runner = CliRunner()


class ScriptedProvider:
    """Proveedor de prueba: responde con texto fijo o falla siempre con el error dado."""

    def __init__(self, name: str, error: Exception | None = None) -> None:
        self.name = name
        self.error = error
        self.models: list[str | None] = []

    def complete(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Completion:
        self.models.append(model)
        if self.error:
            raise self.error
        return Completion(
            text="PROMESA_DE_PAGO", model=model or "m", provider=self.name, latency_ms=12
        )

    def stream(
        self, messages: Sequence[Message], *, model: str | None = None, temperature: float = 0.2
    ) -> Iterator[str]:
        self.models.append(model)
        if self.error:
            raise self.error
        yield from ["PROMESA", "_DE_PAGO"]

    def list_models(self) -> list[str]:
        return ["llama3.2", "tinyllama"]

    def close(self) -> None:
        pass

    def __enter__(self) -> ScriptedProvider:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


@pytest.fixture
def fake_chain(monkeypatch: pytest.MonkeyPatch) -> list[ScriptedProvider]:
    chain: list[ScriptedProvider] = [ScriptedProvider("ollama")]
    monkeypatch.setattr(cli, "build_gateway", lambda order: Gateway(chain, attempts=1))
    return chain


def test_help_is_in_spanish() -> None:
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    for text in ("pregunta", "compara", "modelos", "Muestra esta ayuda", "Comandos"):
        assert text in result.output
    assert "Install completion" not in result.output
    assert " ask " not in result.output  # los alias en inglés quedan ocultos


def test_pregunta_streams_and_passes_model(fake_chain: list[ScriptedProvider]) -> None:
    result = runner.invoke(
        cli.app, ["pregunta", "Me comprometo a pagar el viernes", "-m", "llama3.2"]
    )
    assert result.exit_code == 0
    assert "PROMESA_DE_PAGO" in result.output
    assert fake_chain[0].models == ["llama3.2"]


def test_pregunta_without_stream_shows_provider(fake_chain: list[ScriptedProvider]) -> None:
    result = runner.invoke(cli.app, ["pregunta", "hola", "--sin-stream"])
    assert result.exit_code == 0
    assert "[ollama · m · 12 ms]" in result.output


def test_english_alias_still_works(fake_chain: list[ScriptedProvider]) -> None:
    assert runner.invoke(cli.app, ["ask", "hola"]).exit_code == 0


def test_all_failing_exits_1_with_hint(fake_chain: list[ScriptedProvider]) -> None:
    fake_chain[0].error = ProviderUnavailableError("ollama", "no se pudo conectar")
    result = runner.invoke(cli.app, ["-v", "pregunta", "hola"])
    assert result.exit_code == 1
    assert "Ningún proveedor respondió" in result.output
    assert "Sugerencia" in result.output


def test_authentication_error_exits_1(fake_chain: list[ScriptedProvider]) -> None:
    fake_chain[0].error = AuthenticationError("groq", "falta GROQ_API_KEY")
    result = runner.invoke(cli.app, ["pregunta", "hola", "--sin-stream"])
    assert result.exit_code == 1
    assert "GROQ_API_KEY" in result.output


def test_compara_shows_each_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = {
        "ollama": ScriptedProvider("ollama"),
        "groq": ScriptedProvider("groq", AuthenticationError("groq", "falta GROQ_API_KEY")),
    }
    monkeypatch.setattr(cli, "build_provider", lambda name, settings: providers[name])
    result = runner.invoke(cli.app, ["compara", "Resume la gestión"])
    assert result.exit_code == 0
    assert "proveedor" in result.output
    assert "ollama" in result.output
    assert "falta GROQ_API_KEY" in result.output


def test_modelos_lists_ollama_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "OllamaProvider", lambda *a, **k: ScriptedProvider("ollama"))
    result = runner.invoke(cli.app, ["modelos"])
    assert result.exit_code == 0
    assert result.output.split() == ["llama3.2", "tinyllama"]
