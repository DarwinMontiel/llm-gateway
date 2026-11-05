"""Ejemplo mínimo (primer laboratorio): llamar a la API HTTP de Ollama sin librerías propias.

Requiere `ollama serve` y `ollama pull tinyllama`. Ejecutar: python examples/01_ollama_http_basico.py
"""

import httpx

response = httpx.post(
    "http://localhost:11434/api/generate",
    json={"model": "tinyllama", "prompt": "Why is the sky blue?", "stream": False},
    timeout=120,
)
response.raise_for_status()
print(response.json()["response"])
