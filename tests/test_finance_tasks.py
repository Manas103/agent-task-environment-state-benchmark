import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.finance import schema
from src.finance.tasks import build_corpus


def test_corpus_is_420_tasks_84_per_family_140_mistakes():
    conn = schema.get_finance_conn()
    conn.autocommit = True
    schema.reset_schema(conn)
    try:
        with conn.cursor() as cur:
            tasks = build_corpus(cur, seed=2026)
        assert len(tasks) == 420
        by_family: dict[str, int] = {}
        for t in tasks:
            by_family[t.family] = by_family.get(t.family, 0) + 1
        assert len(by_family) == 5
        assert all(count == 84 for count in by_family.values())
        assert sum(t.is_mistake for t in tasks) == 140
    finally:
        conn.close()
