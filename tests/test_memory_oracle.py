import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory.oracle import grade
from src.memory.tasks import Task


def test_recall_passes_only_if_the_expected_fact_id_is_in_top_k():
    task = Task("recall", "u1", "q", "home_city", "Seattle", expected_fact_id=7)
    top_k_with = [{"id": 7, "session_id": 0, "value": "Seattle", "score": 2}]
    top_k_without = [{"id": 99, "session_id": 0, "value": "Austin", "score": 2}]
    assert grade(task, top_k_with) is True
    assert grade(task, top_k_without) is False


def test_freshness_fails_if_the_top_ranked_value_is_not_the_expected_one():
    task = Task("freshness", "u1", "q", "job_title", "backend engineer", expected_fact_id=7)
    fresh = [{"id": 7, "session_id": 2, "value": "backend engineer", "score": 2}]
    stale = [{"id": 3, "session_id": 1, "value": "designer", "score": 2}]
    assert grade(task, fresh) is True
    assert grade(task, stale) is False


def test_isolation_fails_if_any_top_k_result_belongs_to_another_user():
    task = Task("isolation", "target_user", "q", "home_city", "Seattle", expected_fact_id=7)
    clean = [{"id": 7, "user_id": "target_user", "session_id": 0, "value": "Seattle", "score": 2}]
    leaked = [{"id": 7, "user_id": "target_user", "score": 2}, {"id": 42, "user_id": "distractor_0007", "score": 2}]
    assert grade(task, clean) is True
    assert grade(task, leaked) is False


def test_abstention_passes_only_on_a_true_abstain():
    task = Task("abstention", "u1", "q", "allergy", None, expected_fact_id=None)
    correct_abstain = [{"id": 1, "session_id": 0, "value": "x", "score": 0}]
    wrong_guess = [{"id": 1, "session_id": 0, "value": "peanuts", "score": 3}]
    assert grade(task, correct_abstain) is True
    assert grade(task, wrong_guess) is False
