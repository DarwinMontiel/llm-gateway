"""Clasificar notas de gestión de cobranza con un modelo local y respaldo en la nube.

Lee `examples/datos/gestiones_ficticias.csv` (notas inventadas, sin datos reales) y asigna a
cada una una etiqueta de una lista cerrada. Si el modelo responde algo fuera de la lista, la
nota queda como `revisar` para un humano: el modelo sugiere, no decide.

Ejecutar: python examples/03_clasificar_gestiones.py
"""

from __future__ import annotations

import csv
import logging
import unicodedata
from collections import Counter
from pathlib import Path

from puente_llm import AllProvidersFailedError
from puente_llm.config import build_gateway

ETIQUETAS = {
    "promesa_de_pago": "el cliente se compromete a pagar o acepta un acuerdo",
    "ilocalizable": "no se logra hablar con el titular o el contacto no es válido",
    "reclamo": "el cliente afirma que ya pagó o pide verificar la obligación",
    "renuencia": "el cliente se niega a pagar o rechaza el contacto",
    "dificultad_de_pago": "el cliente quiere pagar pero no puede por ahora",
}

SISTEMA = (
    "Clasificas notas de gestión de cobranza. Responde SOLO con una de estas etiquetas, "
    "sin explicación:\n" + "\n".join(f"- {k}: {v}" for k, v in ETIQUETAS.items())
)

DATOS = Path(__file__).parent / "datos" / "gestiones_ficticias.csv"


def normalizar_etiqueta(respuesta: str) -> str:
    """Convierte la respuesta del modelo a una etiqueta válida o ``revisar``."""
    texto = unicodedata.normalize("NFKD", respuesta).encode("ascii", "ignore").decode()
    texto = texto.strip().strip(".`*\"' ").lower().replace(" ", "_")
    return next((etiqueta for etiqueta in ETIQUETAS if etiqueta in texto), "revisar")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="  · %(message)s")
    with DATOS.open(encoding="utf-8") as archivo:
        gestiones = list(csv.DictReader(archivo))

    conteo: Counter[str] = Counter()
    with build_gateway(["ollama", "groq"]) as gateway:
        for gestion in gestiones:
            try:
                respuesta = gateway.complete(gestion["nota"], system=SISTEMA, temperature=0)
            except AllProvidersFailedError as error:
                sugerencia = "Inicia Ollama (ollama serve) o define GROQ_API_KEY."
                raise SystemExit(f"{error}\n{sugerencia}") from error
            etiqueta = normalizar_etiqueta(respuesta.text)
            conteo[etiqueta] += 1
            print(f"{gestion['id']}  {etiqueta:<20} [{respuesta.provider}]  {gestion['nota'][:60]}")

    print("\nResumen:")
    for etiqueta, cantidad in conteo.most_common():
        print(f"  {etiqueta:<20} {cantidad}")


if __name__ == "__main__":
    main()
