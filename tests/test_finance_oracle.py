import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.finance import oracle, schema
from src.finance.tools import TOOL_BY_FAMILY


def test_oracle_catches_every_injected_mistake_and_passes_every_correct_task():
    conn = schema.get_finance_conn()
    conn.autocommit = True
    schema.reset_schema(conn)
    try:
        with conn.cursor() as cur:
            from src.finance.tasks import build_corpus

            tasks = build_corpus(cur, seed=2026)
            for task in tasks:
                tool = TOOL_BY_FAMILY[task.family]
                result = tool(cur, **task.tool_args)
                assert result["ok"] is True
                ok = oracle.grade(cur, task)
                assert ok == (not task.is_mistake), (
                    f"{task.task_id} ({task.family}): expected oracle_pass={not task.is_mistake}, got {ok}"
                )
    finally:
        conn.close()
