"""flakelens CLI.

    flakelens cases.json --runs 10 --provider mymod:call --out report.md
"""
from __future__ import annotations
import argparse, importlib, sys
from .runner import load_cases, run_suite
from .report import to_markdown, to_json


def _resolve(spec: str):
    """'package.module:function' -> callable(prompt)->str"""
    if ":" not in spec:
        raise SystemExit(f"--provider must be 'module:function', got '{spec}'")
    mod, fn = spec.split(":", 1)
    sys.path.insert(0, ".")
    try:
        m = importlib.import_module(mod)
    except ImportError as e:
        raise SystemExit(f"cannot import '{mod}': {e}")
    if not hasattr(m, fn):
        raise SystemExit(f"'{mod}' has no attribute '{fn}'")
    return getattr(m, fn)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="flakelens",
        description="Find which LLM failures are real and which are just flaky.")
    p.add_argument("cases", help="JSON file of test cases")
    p.add_argument("--provider", required=True,
                   help="module:function taking a prompt, returning a string")
    p.add_argument("--runs", type=int, default=10,
                   help="repeat runs per case (default 10)")
    p.add_argument("--out", default="flakelens-report.md")
    p.add_argument("--json", dest="json_out", default=None)
    p.add_argument("--fail-on-flaky", action="store_true",
                   help="exit non-zero for flaky cases too, not just broken ones")
    a = p.parse_args(argv)

    if a.runs < 2:
        raise SystemExit("--runs must be >= 2; flakiness needs repeats")

    results = run_suite(_resolve(a.provider), load_cases(a.cases), n=a.runs)
    md = to_markdown(results, a.runs)
    with open(a.out, "w") as f:
        f.write(md)
    if a.json_out:
        with open(a.json_out, "w") as f:
            f.write(to_json(results, a.runs))
    print(md)

    broken = sum(1 for r in results if r.status == "FAIL")
    flaky  = sum(1 for r in results if r.status == "FLAKY")
    if broken:
        return 1
    if flaky and a.fail_on_flaky:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
