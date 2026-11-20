"""The transcript-only judge for the finance-workflow extension: the same
deterministic stand-in convention as `src/judge/deterministic_judge.py` and
`src/memory/judge.py`. It sees only the tool's own return value, never the
oracle's expected value, and passes whenever the tool reported ok=True,
which every call in this corpus does regardless of whether an argument was
swapped (see tools.py's module docstring). This is exactly why the judge
cannot do better than 420/420 on this corpus while the oracle, which reads
real final state, catches every one of the 140 injected mistakes.
"""

from __future__ import annotations


def judge_pass(tool_result: dict) -> bool:
    return bool(tool_result.get("ok"))
