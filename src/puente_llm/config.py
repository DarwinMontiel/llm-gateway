"""Configuración por entorno (o ``.env``) y fábricas de proveedores y gateway."""

from __future__ import annotations

import logging

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from puente_llm.gateway import Gateway
from puente_llm.providers import GroqProvider, OllamaProvider
from puente_llm.providers.base import Provider

logger = logging.getLogger(__name__)

PROVIDERS = ("ollama", "groq")


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
    raise ValueError(f"proveedor desconocido: {name} (usa {' o '.join(PROVIDERS)})")


def build_gateway(order: list[str], settings: Settings | None = None) -> Gateway:
    """Construye la cadena de proveedores en el orden indicado.

    Un proveedor de **respaldo** sin credenciales se omite con un aviso: quien solo tiene
    Ollama puede usar la cadena "local primero" sin configurar la nube. Si el proveedor sin
    credenciales es el primero (o el único), se conserva y el error de autenticación aparece al
    usarlo, con un mensaje claro.
    """
    settings = settings or Settings()
    providers: list[Provider] = []
    for position, name in enumerate(order):
        provider = build_provider(name, settings)
        if position > 0 and not getattr(provider, "configured", True):
            logger.warning("se omite el respaldo %s: no tiene credenciales configuradas", name)
            _close(provider)
            continue
        providers.append(provider)
    return Gateway(providers)


def _close(provider: Provider) -> None:
    close = getattr(provider, "close", None)
    if callable(close):
        close()
