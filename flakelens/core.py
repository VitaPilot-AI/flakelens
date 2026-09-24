"""Statistical core: is this case actually flaky, or did we just get unlucky?"""
from __future__ import annotations
import math, statistics, time
from dataclasses import dataclass, field
from typing import Callable, Any


def wilson(passes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a pass rate.

    Normal-approximation intervals collapse to zero width at 0/n and n/n,
    which is exactly where flakiness questions live. Wilson does not.
    """
    if n == 0:
        return (0.0, 1.0)
    p = passes / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def runs_needed(target_lo: float = 0.95, z: float = 1.96) -> int:
    """Minimum all-pass runs before the 95% lower bound clears target_lo."""
    n = 1
    while n < 10000:
        if wilson(n, n, z)[0] >= target_lo:
            return n
        n += 1
    return n


@dataclass
class Case:
    id: str
    prompt: str
    checks: dict = field(default_factory=dict)


@dataclass
class Result:
    case_id: str
    n: int
    passes: int
    failed_checks: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    latencies_ms: list = field(default_factory=list)
    outputs: list = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.passes / self.n if self.n else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.passes, self.n)

    @property
    def status(self) -> str:
        if self.passes == self.n:
            return "PASS"
        if self.passes == 0:
            return "FAIL"
        return "FLAKY"

    @property
    def distinct_outputs(self) -> int:
        return len(set(self.outputs))

    @property
    def p50_ms(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]

    def verdict(self) -> str:
        lo, hi = self.ci
        if self.status == "PASS":
            return f"passed {self.n}/{self.n}; true rate >= {lo:.0%} (95% CI)"
        if self.status == "FAIL":
            return f"failed {self.n}/{self.n}; true rate <= {hi:.0%} (95% CI)"
        return (f"passed {self.passes}/{self.n} = {self.rate:.0%}; "
                f"95% CI [{lo:.0%}, {hi:.0%}] — nondeterministic")
