from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from puente_llm import RateLimitedError
from puente_llm.providers.base import parse_retry_after, raise_for_status

NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("3", 3.0),
        (" 1.5 ", 1.5),
        ("-2", 0.0),
        ("Wed, 21 Oct 2026 07:28:30 GMT", 30.0),  # fecha HTTP: 30 s después de NOW
        ("Wed, 21 Oct 2026 07:27:00 GMT", 0.0),  # fecha ya pasada
        ("inf", None),
        ("pronto", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_retry_after(header: str | None, expected: float | None) -> None:
    assert parse_retry_after(header, now=NOW) == expected


def test_429_with_http_date_is_rate_limited_not_value_error() -> None:
    request = httpx.Request("POST", "http://test/chat/completions")
    response = httpx.Response(
        429, headers={"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"}, request=request
    )
    with pytest.raises(RateLimitedError) as info:
        raise_for_status("groq", response)
    assert info.value.retry_after == 0.0
