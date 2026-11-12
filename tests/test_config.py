from __future__ import annotations

import pytest

from puente_llm import AuthenticationError, Message
from puente_llm.config import Settings, build_gateway, build_provider
from puente_llm.providers import GroqProvider, OllamaProvider


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://gpu-box:11434")
    monkeypatch.setenv("GROQ_API_KEY", "secreto")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.ollama_url == "http://gpu-box:11434"
    assert settings.groq_api_key is not None
    assert "secreto" not in repr(settings)  # SecretStr no se filtra en logs


def test_build_gateway_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    gateway = build_gateway(["ollama", "groq"], Settings(_env_file=None))  # type: ignore[call-arg]
    assert [type(p) for p in gateway.providers] == [OllamaProvider, GroqProvider]


def test_groq_without_key_fails_on_use_and_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    groq = build_provider("groq", settings)
    with pytest.raises(AuthenticationError, match="GROQ_API_KEY"):
        groq.complete([Message.user("hola")])
    with pytest.raises(ValueError, match="desconocido"):
        build_provider("openai", settings)


def test_auto_without_groq_key_keeps_only_ollama(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Quien solo tiene Ollama puede usar la cadena "local primero" sin configurar la nube."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with build_gateway(["ollama", "groq"], Settings(_env_file=None)) as gateway:  # type: ignore[call-arg]
        assert [type(p) for p in gateway.providers] == [OllamaProvider]
    assert "se omite el respaldo groq" in caplog.text


def test_groq_alone_without_key_is_kept_to_report_the_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    gateway = build_gateway(["groq"], Settings(_env_file=None))  # type: ignore[call-arg]
    with gateway, pytest.raises(AuthenticationError):
        gateway.complete("hola")
