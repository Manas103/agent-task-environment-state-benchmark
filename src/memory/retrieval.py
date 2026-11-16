"""Lexical retrieval over a fact pool: token-overlap scoring, ties broken
toward the more recent session. Deliberately simple (not an embedding
model) so a recall miss or a freshness failure is traceable to an exact,
inspectable score, not a black-box similarity number.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {"s", "is", "i", "m"}  # dropped so "my", "what", "is" alone never counts as a topical match

TOP_K = 10
MIN_SCORE_TO_ANSWER = 2  # calibrated on a held-out dev set; see measure.py


def tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def score_and_rank(candidates: list[dict], query_text: str, k: int = TOP_K) -> list[dict]:
    query_tokens = tokenize(query_text)
    scored = []
    for fact in candidates:
        overlap = len(query_tokens & tokenize(fact["text"]))
        scored.append({**fact, "score": overlap})
    scored.sort(key=lambda f: (f["score"], f["session_id"]), reverse=True)
    return scored[:k]


def best_answer(top_k: list[dict], min_score: int = MIN_SCORE_TO_ANSWER) -> dict | None:
    """The top-ranked candidate, or None (abstain) if its score does not
    clear the threshold. Abstention is a retrieval-confidence decision, not
    a separate model call."""
    if not top_k or top_k[0]["score"] < min_score:
        return None
    return top_k[0]
