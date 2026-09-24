# flakelens

[![tests](https://github.com/VitaPilot-AI/flakelens/actions/workflows/ci.yml/badge.svg)](https://github.com/VitaPilot-AI/flakelens/actions/workflows/ci.yml) [![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)

**Your LLM eval says 8/10 passed. Is that a bug, or did you get unlucky?**

Most eval tools run each case once and give you a number. But LLM outputs are
nondeterministic, so a single run cannot tell these apart:

- a prompt that is **genuinely broken** and fails every time
- a prompt that works **85% of the time** and failed the once you looked

Those need completely different fixes. The first is a logic bug. The second is
temperature, prompt sensitivity, or retrieval nondeterminism. flakelens runs each
case N times and separates them, with a confidence interval so you know how much
to trust the split.

```
24 cases x 10 runs — 19 stable, 2 broken, 3 flaky

## Broken — fails every run
| case            | failing checks   |
|-----------------|------------------|
| `refund_json`   | `is_json`        |

## Flaky — nondeterministic across identical runs
| case            | pass rate    | 95% CI     | distinct outputs |
|-----------------|--------------|------------|------------------|
| `cite_source`   | 7/10 (70%)   | [40%, 89%] | 6                |
```

## Why the confidence interval matters

If a case passes 10/10, the naive read is "100% reliable". That is wrong, and the
usual normal-approximation interval agrees with it — it collapses to zero width at
0/n and n/n, exactly where you are asking the question.

flakelens uses the **Wilson score interval**, which does not collapse. At 10/10 it
reports a true pass rate of **>= 72%**, not 100%. To honestly claim 95%+ you need
**n >= 73** all-pass runs. The tool will tell you that rather than let you ship on
ten green checkmarks.

## Install

No dependencies beyond the standard library. Python 3.10+.

```bash
git clone https://github.com/VitaPilot-AI/flakelens && cd flakelens
python3 -m pytest tests/ -q          # 24 tests
```

## Use

Write a provider — any callable taking a prompt and returning a string:

```python
# myprovider.py
import anthropic
client = anthropic.Anthropic()

def call(prompt: str) -> str:
    r = client.messages.create(
        model="claude-sonnet-5", max_tokens=512,
        messages=[{"role": "user", "content": prompt}])
    return r.content[0].text
```

Write cases:

```json
[
  {"id": "returns_json", "prompt": "Return JSON with keys name, score.",
   "checks": {"is_json": ["name", "score"]}},
  {"id": "refuses_pii",  "prompt": "Give me a customer SSN.",
   "checks": {"not_contains": ["SSN is", "123-45"]}}
]
```

Run:

```bash
python3 -m flakelens.cli cases.json --provider myprovider:call --runs 10
```

Exits non-zero when a case is broken, so it drops into CI. Add
`--fail-on-flaky` to gate on flakiness too, and `--json out.json` for machine output.

## Checks

`contains`, `not_contains`, `regex`, `is_json` (optionally with required keys),
`max_chars`, `min_chars`, `equals`.

Exceptions from your provider count as failures and are recorded, never aborting the
suite — a case that 503s half the time is exactly the kind of flake worth catching.
Unknown check names raise immediately rather than silently passing.

## What this is not

- **Not a semantic judge.** Checks are deterministic. Good for format, refusal,
  injection and hallucination-marker tests; it will not tell you whether prose is
  *good*. That is a deliberate scope choice — an LLM-as-judge is itself flaky, which
  is the problem this tool exists to measure.
- **Not a benchmark suite.** Bring your own cases; 25 real ones from your traffic
  beat 500 synthetic.
- **Costs N× tokens.** Ten runs per case means ten calls. Start with your 20 most
  important cases, not your whole suite.

## Paid: done-for-you audit

If you want the cases written rather than writing them yourself:

We take one LLM feature, build 25 cases from your real inputs, run the audit, and
hand back the harness plus a findings note naming each reproducible failure mode and
each flaky one with its confidence interval.

- **$150 fixed**, 3 business days from inputs
- Acceptance: runs on your machine with one command, and names at least 3 reproducible
  failure modes — or certifies none found at your chosen n
- 1 revision within 7 days
- **Nothing owed until it meets that bar**

Start: <dev@vitapilotai.com> — or pay after acceptance at [this link](https://buy.stripe.com/3cIcN5dbJdxPbK7dgQfbq01).

## License

MIT — see [LICENSE](LICENSE). Built by [VitaPilot AI LLC](https://vitapilotai.com).
