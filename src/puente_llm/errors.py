"""Jerarquía de errores: permite decidir qué reintentar y cuándo pasar al siguiente proveedor."""

from __future__ import annotations


class ProviderError(Exception):
    """Error base de un proveedor."""

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider


class ProviderUnavailableError(ProviderError):
    """Conexión rechazada, timeout o error 5xx: reintentable y motivo de fallback."""


class RateLimitedError(ProviderError):
    """HTTP 429: reintentable respetando ``retry_after``."""

    def __init__(self, provider: str, message: str, retry_after: float | None = None) -> None:
        super().__init__(provider, message)
        self.retry_after = retry_after


class AuthenticationError(ProviderError):
    """Credencial ausente o rechazada: no se reintenta."""


class AllProvidersFailedError(Exception):
    """Ningún proveedor de la cadena pudo responder."""

    def __init__(self, errors: list[ProviderError]) -> None:
        detail = "; ".join(str(e) for e in errors)
        super().__init__(f"Ningún proveedor respondió: {detail}")
        self.errors = errors
