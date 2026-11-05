# Changelog

## [1.0.0] - 2026-11-05

### Agregado
- Paquete `llm_gateway` con proveedores Ollama (NDJSON) y Groq (SSE, API compatible con OpenAI).
- Jerarquía de errores, reintentos con backoff exponencial y `Retry-After`, *fallback* entre proveedores.
- CLI `llm` (`ask`, `compare`, `models`) y configuración por `.env` con `SecretStr`.
- 24 pruebas sin red con `httpx.MockTransport` y CI en Python 3.11–3.13.

### Cambiado
- Las notas de laboratorio originales pasan a `docs/guia-ollama-groq.md`; el ejemplo inicial a `examples/`.

### Seguridad
- Eliminada del README una API key publicada por error; se activa el *secret scanning* de GitHub con protección de push.

## [0.1.0] - 2024-09-03
- Notas de laboratorio: Ollama local y API de Groq con curl; primer ejemplo en Python.
