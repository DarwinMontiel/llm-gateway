from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def make_client() -> Callable[[Handler, str], httpx.Client]:
    """Cliente httpx con transporte simulado: las pruebas nunca salen a la red."""

    def factory(handler: Handler, base_url: str = "http://test") -> httpx.Client:
        return httpx.Client(base_url=base_url, transport=httpx.MockTransport(handler))

    return factory


@pytest.fixture
def ollama_stream_body() -> bytes:
    return (FIXTURES / "ollama_generate_stream.ndjson").read_bytes()
