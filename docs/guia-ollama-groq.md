# Guía: LLM locales con Ollama y en la nube con Groq

Notas de laboratorio de la asignatura *Sistemas Inteligentes* (2024), reorganizadas. Explican
las dos APIs que `puente-llm` envuelve.

## 1. Ollama (modelos locales)

### Instalación

- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`
- **Windows / macOS:** instalador desde <https://ollama.com/download>

### Servidor y modelos

```bash
ollama serve                 # inicia la API en http://localhost:11434
ollama pull tinyllama        # descarga un modelo pequeño (≈640 MB)
ollama list                  # modelos descargados
ollama run tinyllama "¿Por qué el cielo es azul?"
```

Catálogo de modelos: <https://ollama.com/library>.

### API HTTP

```bash
# Respuesta en streaming (NDJSON: una línea JSON por fragmento)
curl http://localhost:11434/api/generate -d '{"model": "tinyllama", "prompt": "¿Por qué el cielo es azul?"}'

# Respuesta completa en un solo JSON
curl http://localhost:11434/api/generate -d '{"model": "tinyllama", "prompt": "¿Por qué el cielo es azul?", "stream": false}'
```

En streaming cada línea trae un fragmento en `response` y la última trae `"done": true` con
métricas (`eval_count`, `total_duration`…). El archivo
[`tests/fixtures/ollama_generate_stream.ndjson`](../tests/fixtures/ollama_generate_stream.ndjson)
es una captura real de esa salida y se usa en las pruebas del parser.

> **Lección del laboratorio:** `tinyllama` respondió que el cielo es azul "por el cromo en sus
> pigmentos". Los modelos muy pequeños alucinan con facilidad; por eso existe `puente compara`,
> que envía la misma pregunta a un modelo local y a uno más grande en la nube. En cobranza la
> lección pesa más: una etiqueta inventada cambia la gestión de un cliente, así que el ejemplo
> de clasificación acepta solo una lista cerrada y deja lo demás para revisión humana.

Para conversaciones con roles (`system`, `user`, `assistant`) se usa `POST /api/chat`, que es
el endpoint que utiliza `OllamaProvider`.

## 2. Groq (modelos en la nube, API compatible con OpenAI)

1. Crear una cuenta en <https://console.groq.com> y generar una API key.
2. Guardarla **solo** en el entorno o en un archivo `.env` que no se versiona:

   ```bash
   export GROQ_API_KEY="gsk_..."      # PowerShell: $env:GROQ_API_KEY = "gsk_..."
   ```

3. Probar la API:

   ```bash
   curl https://api.groq.com/openai/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $GROQ_API_KEY" \
     -d '{"model": "llama-3.1-8b-instant",
          "messages": [{"role": "user", "content": "¿Por qué el cielo es azul?"}]}'
   ```

Con `"stream": true` la respuesta llega como *Server-Sent Events* (`data: {...}` y al final
`data: [DONE]`), formato que procesa `GroqProvider`.

> **Seguridad:** una API key nunca va en un README, un notebook ni un commit. Si se publica por
> error, se debe **revocar de inmediato** en la consola del proveedor; borrarla del archivo no
> basta porque queda en el historial de Git. Herramientas como el *secret scanning* de GitHub o
> `gitleaks` detectan estas fugas.
