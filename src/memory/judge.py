"""A transcript-only judge: it sees the retrieved top-k facts and whatever
answer the system submitted, and nothing else (no ground truth, no
knowledge of which fact is current, no knowledge of which user is being
asked about). It passes whenever the submitted answer looks supported by
the transcript, which structurally cannot tell a fresh answer from a stale
one, or a correct abstention from a lucky one, which is exactly why
measure.py finds a gap against the real oracle. Same deterministic-stand-in
convention as `src/judge/deterministic_judge.py` at the top level of this
repository.
"""

from __future__ import annotations


def judge_pass(top_k: list[dict], submitted_answer: str | None) -> bool:
    if submitted_answer is None:
        # a transcript reader has no way to tell a correct abstention from
        # one that quietly missed an answer that was there to find; this
        # judge gives abstention the benefit of the doubt either way
        return True
    return any(f["value"] == submitted_answer for f in top_k)
