"""Repeat-run each case and classify PASS / FAIL / FLAKY."""
from __future__ import annotations
import json, time
from typing import Callable
from .core import Case, Result
from .checks import REGISTRY


def run_case(fn: Callable[[str], str], case: Case, n: int = 10) -> Result:
    r = Result(case_id=case.id, n=n, passes=0)
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            out = fn(case.prompt)
        except Exception as e:
            r.errors.append(f"{type(e).__name__}: {e}")
            r.latencies_ms.append((time.perf_counter() - t0) * 1000)
            continue
        r.latencies_ms.append((time.perf_counter() - t0) * 1000)
        r.outputs.append(out)
        ok = True
        for name, arg in case.checks.items():
            fnc = REGISTRY.get(name)
            if fnc is None:
                raise ValueError(f"unknown check '{name}' in case '{case.id}'")
            if not fnc(out, arg):
                r.failed_checks[name] = r.failed_checks.get(name, 0) + 1
                ok = False
        if ok:
            r.passes += 1
    return r


def run_suite(fn, cases: list[Case], n: int = 10) -> list[Result]:
    return [run_case(fn, c, n) for c in cases]


def load_cases(path: str) -> list[Case]:
    with open(path) as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError("cases file must be a JSON list")
    return [Case(id=c["id"], prompt=c["prompt"], checks=c.get("checks", {}))
            for c in raw]
