"""El mismo objetivo con llm-gateway: modelo local primero y Groq como respaldo.

Si Ollama no está corriendo, el gateway reintenta y responde con Groq (requiere GROQ_API_KEY).
Ejecutar: python examples/02_gateway_con_fallback.py
"""

from puente_llm.config import build_gateway

gateway = build_gateway(["ollama", "groq"])

completion = gateway.complete(
    "Explica en dos frases por qué el cielo es azul.",
    system="Eres un profesor de física. Responde en español, con precisión.",
)
print(completion.text)
print(f"\n→ {completion.provider} · {completion.model} · {completion.latency_ms:.0f} ms")

print("\nStreaming:")
for chunk in gateway.stream("Dame tres usos de la automatización con IA en cobranzas."):
    print(chunk, end="", flush=True)
print()
