from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples"


def load_example(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clasificador = load_example("03_clasificar_gestiones")


@pytest.mark.parametrize(
    ("respuesta", "esperada"),
    [
        ("promesa_de_pago", "promesa_de_pago"),
        ("  Promesa de pago.", "promesa_de_pago"),
        ("**reclamo**", "reclamo"),
        ("Dificultad de pago", "dificultad_de_pago"),
        ("Ilocalizable", "ilocalizable"),
        ("Creo que el cliente está molesto", "revisar"),
    ],
)
def test_normalizar_etiqueta(respuesta: str, esperada: str) -> None:
    assert clasificador.normalizar_etiqueta(respuesta) == esperada


def test_dataset_ficticio_is_well_formed() -> None:
    with clasificador.DATOS.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) >= 10
    assert all(fila["id"].startswith("G-") and fila["nota"] for fila in filas)
