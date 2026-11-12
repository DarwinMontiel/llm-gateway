# Registro de cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[versionado semántico](https://semver.org/lang/es/).

## [2.0.0] - 2026-11-12

### Cambiado (incompatible)
- El proyecto pasa a llamarse **puente-llm**: el paquete `llm_gateway` ahora es `puente_llm` y
  el comando `llm` ahora es `puente`.
- Subcomandos en español: `pregunta`, `compara` y `modelos` (los nombres `ask`, `compare` y
  `models` quedan como alias ocultos). Opciones `--proveedor`, `--sistema`, `--modelo` y
  `--stream/--sin-stream`; ayuda en español.

### Agregado
- `puente --detalle` (`-v`) muestra en el log los reintentos y los cambios de proveedor.
- `Gateway.stream` acepta `model`, igual que `complete`.
- `Gateway` y los proveedores se pueden usar como *context manager* y cierran sus clientes httpx.
- Ejemplo `03_clasificar_gestiones.py` con notas de gestión ficticias y prompts de cobranza en
  los ejemplos 01 y 02.
- Decisiones de diseño documentadas como ADR en `docs/adr/`.
- El CI construye el paquete y prueba el comando instalado.

### Corregido
- El modo "local primero" ya no falla cuando falta `GROQ_API_KEY`: el respaldo sin credenciales
  se omite con un aviso y Ollama responde.
- `stream` reintenta con backoff antes del primer fragmento, como `complete`, en lugar de cambiar
  de proveedor al primer fallo.
- Una cabecera `Retry-After` con fecha HTTP ya no provoca `ValueError`; se convierte a segundos.

## [1.0.0] - 2026-11-05

### Agregado
- Paquete `llm_gateway` con proveedores Ollama (NDJSON) y Groq (SSE, API compatible con OpenAI).
- Jerarquía de errores, reintentos con backoff exponencial y `Retry-After`, *fallback* entre proveedores.
- CLI `llm` (`ask`, `compare`, `models`) y configuración por `.env` con `SecretStr`.
- 24 pruebas sin red con `httpx.MockTransport` y CI en Python 3.11–3.13.

### Cambiado
- Las notas de laboratorio originales pasan a `docs/guia-ollama-groq.md`; el ejemplo inicial a `examples/`.

### Seguridad
- Los ejemplos de configuración usan variables de entorno y un archivo `.env` que no se versiona;
  se activaron el *secret scanning* y la protección de push de GitHub.

## [0.1.0] - 2024-09-03
- Notas de laboratorio: Ollama local y API de Groq con curl; primer ejemplo en Python.
