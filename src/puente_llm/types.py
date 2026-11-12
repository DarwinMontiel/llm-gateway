from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def user(cls, content: str) -> Message:
        return cls("user", content)

    @classmethod
    def system(cls, content: str) -> Message:
        return cls("system", content)


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    model: str
    provider: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def tokens_per_second(self) -> float | None:
        if not self.completion_tokens or self.latency_ms <= 0:
            return None
        return round(self.completion_tokens / (self.latency_ms / 1000), 1)
