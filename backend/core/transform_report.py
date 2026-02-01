from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TransformStep:
    name: str
    rows_in: int
    rows_out: int
    reason: str
    details: dict[str, Any] | None = None


@dataclass
class TransformReport:
    steps: list[TransformStep] = field(default_factory=list)

    def add(
        self,
        name: str,
        *,
        rows_in: int,
        rows_out: int,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.steps.append(
            TransformStep(
                name=str(name),
                rows_in=int(rows_in),
                rows_out=int(rows_out),
                reason=str(reason),
                details=details,
            )
        )
