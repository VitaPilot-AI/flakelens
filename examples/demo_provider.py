"""A deliberately imperfect mock: one broken case, one flaky formatter.

Swap this for a real client call. Kept dependency-free so the demo runs anywhere.
"""
import random

def call(prompt: str) -> str:
    if "JSON" in prompt:    return '{"name":"acme","score":7}'
    if "SSN" in prompt:     return "I can't share personal identifiers."
    if "refund" in prompt:  return "Our refund policy allows returns within 30 days."
    if "Q9" in prompt:      return "Q9 revenue was $4.2M."            # always wrong
    if "bullets" in prompt:                                           # flaky ~50%
        return "- a\n- b\n- c" if random.random() < 0.5 else "a, b, c"
    return ""
