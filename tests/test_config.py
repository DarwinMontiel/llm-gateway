from __future__ import annotations

import pytest

from puente_llm import AuthenticationError
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


def test_groq_without_key_and_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    with pytest.raises(AuthenticationError):
        build_provider("groq", settings)
    with pytest.raises(ValueError, match="desconocido"):
        build_provider("openai", settings)
