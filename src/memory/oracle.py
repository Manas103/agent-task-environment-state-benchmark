"""The expected-state oracle for the memory extension: grades each of the
four qualities against the fact store's real ground truth, never against
what the transcript-reading judge saw. Mirrors the top-level repo's own
oracle/judge split (`src/oracle/` vs `src/judge/`), applied to memory
instead of CRM/ticketing/inventory state.
"""

from __future__ import annotations

from src.memory.retrieval import best_answer
from src.memory.tasks import Task


def grade_recall(task: Task, top_k: list[dict]) -> bool:
    return any(f["id"] == task.expected_fact_id for f in top_k)


def grade_freshness(task: Task, top_k: list[dict]) -> bool:
    answer = best_answer(top_k)
    return answer is not None and answer["value"] == task.expected_value


def grade_isolation(task: Task, top_k: list[dict]) -> bool:
    return all(f.get("user_id", task.user_id) == task.user_id for f in top_k)


def grade_abstention(task: Task, top_k: list[dict]) -> bool:
    answer = best_answer(top_k)
    if task.expected_value is None:
        return answer is None
    return answer is not None and answer["value"] == task.expected_value


GRADERS = {
    "recall": grade_recall,
    "freshness": grade_freshness,
    "isolation": grade_isolation,
    "abstention": grade_abstention,
}


def grade(task: Task, top_k: list[dict]) -> bool:
    return GRADERS[task.kind](task, top_k)
