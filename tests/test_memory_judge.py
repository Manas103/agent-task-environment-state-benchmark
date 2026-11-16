import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory.judge import judge_pass


def test_judge_passes_a_correct_answer():
    top_k = [{"id": 1, "value": "backend engineer"}]
    assert judge_pass(top_k, "backend engineer") is True


def test_judge_overcredits_a_stale_answer_that_still_appears_in_the_transcript():
    """The actual mechanism behind this repository's measured overcredit
    gap: the judge only checks that the submitted value appears somewhere
    in what was retrieved, which a stale (superseded) value still does."""
    top_k = [{"id": 1, "value": "designer"}, {"id": 2, "value": "backend engineer"}]
    stale_answer = "designer"  # superseded; the real current value is "backend engineer"
    assert judge_pass(top_k, stale_answer) is True


def test_judge_rejects_an_answer_absent_from_the_transcript():
    top_k = [{"id": 1, "value": "backend engineer"}]
    assert judge_pass(top_k, "astronaut") is False


def test_judge_always_gives_abstention_the_benefit_of_the_doubt():
    top_k = [{"id": 1, "value": "backend engineer"}]
    assert judge_pass(top_k, None) is True
