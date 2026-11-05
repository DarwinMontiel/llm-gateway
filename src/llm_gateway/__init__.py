"""llm-gateway: una sola interfaz para modelos de lenguaje locales (Ollama) y en la nube (Groq)."""

from llm_gateway.errors import (
    AllProvidersFailedError,
    AuthenticationError,
    ProviderError,
    ProviderUnavailableError,
    RateLimitedError,
)
from llm_gateway.gateway import Gateway
from llm_gateway.types import Completion, Message

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
