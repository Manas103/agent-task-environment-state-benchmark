import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory import store
from src.memory.retrieval import score_and_rank


def test_scoped_retrieval_excludes_a_better_matching_distractor_fact():
    conn = store.get_memory_conn()
    conn.autocommit = True
    store.reset_schema(conn)
    try:
        with conn.cursor() as cur:
            store.insert_fact(cur, "target_user", 0, "home_city", "Austin", "I live in Austin these days.")
            # a distractor whose fact is a stronger lexical match for the same
            # query than the target user's own fact, planted deliberately
            store.insert_fact(cur, "distractor_0001", 5, "home_city", "Seattle", "I live in Seattle these days and love it there.")

            with conn.cursor() as cur2:
                scoped = score_and_rank(store.facts_for_user(cur2, "target_user"), "What city do I live in?")
                unscoped = score_and_rank(store.all_facts_unscoped(cur2), "What city do I live in?")

        assert all(f.get("user_id", "target_user") == "target_user" for f in scoped)
        assert scoped[0]["value"] == "Austin"
        # and the probe is not vacuous: without the scope, the distractor's
        # fact really does outrank the target user's own fact
        assert unscoped[0]["user_id"] == "distractor_0001"
    finally:
        conn.close()
