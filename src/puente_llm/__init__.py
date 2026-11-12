"""puente-llm: una sola interfaz para modelos de lenguaje locales (Ollama) y en la nube (Groq)."""

from puente_llm.errors import (
    AllProvidersFailedError,
    AuthenticationError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitedError,
)
from puente_llm.gateway import Gateway
from puente_llm.types import Completion, Message

__version__ = "1.0.0"

__all__ = [
    "AllProvidersFailedError",
    "AuthenticationError",
    "Completion",
    "Gateway",
    "Message",
    "ProviderError",
    "ProviderUnavailableError",
    "RateLimitedError",
]
