"""Markdown + JSON reporting."""
from __future__ import annotations
import json
from .core import Result, runs_needed


def to_markdown(results: list[Result], n: int) -> str:
    hard  = [r for r in results if r.status == "FAIL"]
    flaky = [r for r in results if r.status == "FLAKY"]
    ok    = [r for r in results if r.status == "PASS"]
    L = ["# Flakiness audit\n",
         f"{len(results)} cases x {n} runs — "
         f"**{len(ok)} stable, {len(hard)} broken, {len(flaky)} flaky**\n"]
    if hard:
        L.append("\n## Broken — fails every run\n")
        L.append("| case | failing checks | note |")
        L.append("|---|---|---|")
        for r in hard:
            why = ", ".join(f"`{k}`" for k in r.failed_checks) or "exception"
            note = r.errors[0][:60] if r.errors else r.verdict()
            L.append(f"| `{r.case_id}` | {why} | {note} |")
    if flaky:
        L.append("\n## Flaky — nondeterministic across identical runs\n")
        L.append("| case | pass rate | 95% CI | distinct outputs | failing |")
        L.append("|---|---|---|---|---|")
        for r in flaky:
            lo, hi = r.ci
            why = ", ".join(f"`{k}`" for k in r.failed_checks) or "error"
            L.append(f"| `{r.case_id}` | {r.passes}/{r.n} ({r.rate:.0%}) | "
                     f"[{lo:.0%}, {hi:.0%}] | {r.distinct_outputs} | {why} |")
        L.append("\nFlaky cases usually mean temperature, prompt sensitivity, or "
                 "retrieval nondeterminism — not a logic bug. They need different "
                 "fixes than the broken ones above.")
    if not hard and not flaky:
        L.append(f"\nNo failures across {n} runs per case. With all-pass at "
                 f"n={n}, the 95% lower bound on each case's true pass rate is "
                 f"{results[0].ci[0]:.0%}.\n" if results else "\nNo cases.\n")
    L.append("\n## Latency\n")
    L.append("| case | p50 ms | p95 ms |")
    L.append("|---|---|---|")
    for r in results:
        L.append(f"| `{r.case_id}` | {r.p50_ms:.0f} | {r.p95_ms:.0f} |")
    L.append(f"\n<sub>Confidence intervals are Wilson score. To claim a true pass "
             f"rate of 95%+ from an all-pass run you need n >= {runs_needed()}.</sub>\n")
    return "\n".join(L)


def to_json(results: list[Result], n: int) -> str:
    return json.dumps({
        "runs_per_case": n,
        "summary": {
            "stable": sum(1 for r in results if r.status == "PASS"),
            "broken": sum(1 for r in results if r.status == "FAIL"),
            "flaky":  sum(1 for r in results if r.status == "FLAKY"),
        },
        "cases": [{
            "id": r.case_id, "status": r.status,
            "passes": r.passes, "runs": r.n, "rate": round(r.rate, 4),
            "ci95": [round(r.ci[0], 4), round(r.ci[1], 4)],
            "distinct_outputs": r.distinct_outputs,
            "failed_checks": r.failed_checks,
            "errors": r.errors[:3],
            "p50_ms": round(r.p50_ms, 1), "p95_ms": round(r.p95_ms, 1),
        } for r in results],
    }, indent=2)
