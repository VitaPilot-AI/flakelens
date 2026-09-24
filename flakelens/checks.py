"""Deterministic checks. Each returns True on pass."""
from __future__ import annotations
import json, re
from typing import Any, Callable


def _terms(arg: Any) -> list[str]:
    return [str(t) for t in (arg if isinstance(arg, list) else [arg])]

def contains(out: str, arg: Any) -> bool:
    return all(t.lower() in out.lower() for t in _terms(arg))

def not_contains(out: str, arg: Any) -> bool:
    return all(t.lower() not in out.lower() for t in _terms(arg))

def regex(out: str, arg: Any) -> bool:
    return re.search(str(arg), out, re.S) is not None

def is_json(out: str, arg: Any) -> bool:
    try:
        obj = json.loads(out)
    except Exception:
        return False
    if isinstance(arg, list):
        return isinstance(obj, dict) and all(k in obj for k in arg)
    return True

def max_chars(out: str, arg: Any) -> bool:
    return len(out) <= int(arg)

def min_chars(out: str, arg: Any) -> bool:
    return len(out) >= int(arg)

def equals(out: str, arg: Any) -> bool:
    return out.strip() == str(arg).strip()

REGISTRY: dict[str, Callable[[str, Any], bool]] = {
    "contains": contains, "not_contains": not_contains, "regex": regex,
    "is_json": is_json, "max_chars": max_chars, "min_chars": min_chars,
    "equals": equals,
}
