"""Invocation-local performance observations for FlowGuard.

The counters in this module are diagnostics only.  They are deliberately
ephemeral: they are not persisted, are not part of any authority fingerprint,
and never change a validation decision.  A caller records work performed by
the real operation that it is already executing; the metrics object never
walks a tree or reads a file by itself.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import monotonic
from typing import Iterator, Mapping


@dataclass
class InvocationMetrics:
    """Small mutable counter bag owned by one invocation."""

    counters: dict[str, int] = field(default_factory=dict)
    phases: dict[str, float] = field(default_factory=dict)

    def inc(self, name: str, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("metric increments must be non-negative")
        self.counters[name] = self.counters.get(name, 0) + int(amount)

    def observe(self, name: str, value: int) -> None:
        """Set a monotonic observation to the greatest seen value."""

        current = self.counters.get(name, 0)
        if value < current:
            raise ValueError(f"metric observation cannot decrease: {name}")
        self.counters[name] = int(value)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        started = monotonic()
        try:
            yield
        finally:
            self.phases[name] = self.phases.get(name, 0.0) + (monotonic() - started)

    def snapshot(self) -> dict[str, object]:
        return {
            "counters": dict(sorted(self.counters.items())),
            "phases_seconds": {
                key: round(value, 6)
                for key, value in sorted(self.phases.items())
            },
        }

    @classmethod
    def from_mapping(cls, values: Mapping[str, int]) -> "InvocationMetrics":
        metrics = cls()
        for key, value in values.items():
            metrics.observe(str(key), int(value))
        return metrics


__all__ = ["InvocationMetrics"]
