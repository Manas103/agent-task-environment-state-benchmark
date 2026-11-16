import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory.retrieval import best_answer, score_and_rank


def test_higher_token_overlap_ranks_first():
    candidates = [
        {"id": 1, "session_id": 0, "value": "Seattle", "text": "I live in Seattle these days."},
        {"id": 2, "session_id": 0, "value": "designer", "text": "I work as a designer."},
    ]
    ranked = score_and_rank(candidates, "What city do I live in?")
    assert ranked[0]["id"] == 1


def test_ties_break_toward_the_more_recent_session():
    candidates = [
        {"id": 1, "session_id": 0, "value": "Seattle", "text": "I live in Seattle these days."},
        {"id": 2, "session_id": 5, "value": "Austin", "text": "I live in Austin these days."},
    ]
    ranked = score_and_rank(candidates, "What city do I live in?")
    assert ranked[0]["id"] == 2


def test_best_answer_abstains_below_the_score_threshold():
    candidates = [{"id": 1, "session_id": 0, "value": "Seattle", "text": "I live in Seattle these days."}]
    assert best_answer(candidates_but_scored_zero(candidates)) is None


def candidates_but_scored_zero(candidates):
    return [{**c, "score": 0} for c in candidates]
