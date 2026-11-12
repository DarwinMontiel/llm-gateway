# 0001 · Proveedores como `Protocol` y errores propios

- **Estado:** aceptada
- **Fecha:** 2026-11-05

## Contexto

Ollama y Groq exponen APIs distintas: Ollama usa `POST /api/chat` con streaming en NDJSON; Groq
es compatible con OpenAI y transmite con *Server-Sent Events*. Sus errores también difieren (una
conexión rechazada en local, un 429 con `Retry-After` en la nube). Usar el SDK de cada proveedor
llevaría esas diferencias, y sus excepciones, al código que consume la librería.

## Decisión

- Cada proveedor es una clase que cumple un `typing.Protocol` con dos métodos: `complete` y
  `stream`. No hay herencia obligatoria.
- Las llamadas se hacen con `httpx` directamente, y cada respuesta HTTP o fallo de red se traduce
  a una jerarquía propia: `ProviderUnavailableError`, `RateLimitedError`, `AuthenticationError`.
- El gateway solo conoce el protocolo y la jerarquía de errores.

## Consecuencias

- Agregar un proveedor (OpenAI, Azure, Bedrock) es una clase nueva; el gateway no cambia.
- Las pruebas usan `httpx.MockTransport` y no dependen de red ni de claves.
- Se mantiene a mano el parseo de dos formatos de streaming; lo cubren pruebas con una captura
  real de Ollama.
