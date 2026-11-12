from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from puente_llm.gateway import Gateway
from puente_llm.providers import GroqProvider, OllamaProvider
from puente_llm.providers.base import Provider


class Settings(BaseSettings):
    """Configuración por entorno / archivo .env (que nunca se versiona)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.1-8b-instant"
    timeout_seconds: float = 60.0


def build_provider(name: str, settings: Settings) -> Provider:
    if name == "ollama":
        return OllamaProvider(settings.ollama_url, settings.ollama_model, settings.timeout_seconds)
    if name == "groq":
        key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
        return GroqProvider(
            key, default_model=settings.groq_model, timeout=settings.timeout_seconds
        )
    raise ValueError(f"proveedor desconocido: {name} (usa ollama o groq)")


def build_gateway(order: list[str], settings: Settings | None = None) -> Gateway:
    settings = settings or Settings()
    return Gateway([build_provider(name, settings) for name in order])
