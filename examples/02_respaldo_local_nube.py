"""El mismo objetivo con puente-llm: modelo local primero y Groq como respaldo.

Si Ollama no responde, el puente reintenta y pasa a Groq (si GROQ_API_KEY está definida).
Sin la clave, funciona solo con Ollama.
Ejecutar: python examples/02_respaldo_local_nube.py
"""

import logging

from puente_llm.config import build_gateway

# Muestra los reintentos y los cambios de proveedor.
logging.basicConfig(level=logging.WARNING, format="  · %(message)s")

GESTION = (
    "Llamada saliente 10:42. Contesta la titular. Dice que la quincena se le retrasó, "
    "reconoce las dos cuotas en mora y se compromete a abonar la mitad el día 15 y el "
    "resto a fin de mes. Pide que no la llamen al trabajo."
)

with build_gateway(["ollama", "groq"]) as gateway:
    resumen = gateway.complete(
        f"Resume esta gestión en una frase para el historial del cliente:\n{GESTION}",
        system="Eres analista de cobranza. Responde en español, sin inventar datos.",
    )
    print(resumen.text)
    print(f"\n→ {resumen.provider} · {resumen.model} · {resumen.latency_ms:.0f} ms")

    print("\nStreaming:")
    for chunk in gateway.stream(
        f"Propón el siguiente paso de gestión, en dos viñetas, para este caso:\n{GESTION}",
        system="Eres coordinador de cobranza. Tono respetuoso, sin presionar al cliente.",
    ):
        print(chunk, end="", flush=True)
    print()
