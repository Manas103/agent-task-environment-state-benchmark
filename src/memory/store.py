"""The fact store for the memory extension: one Postgres table, schema
`memory`, reusing `src.db.get_conn` the same way the three original
environment services do. A fact is append-only; an "update" is a new row
with a later `session_id` for the same (user_id, slot), and freshness is a
retrieval-time question (src/memory/retrieval.py), not something enforced
by overwriting old rows.
"""

from __future__ import annotations

from src.db import get_conn

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS facts (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id INT NOT NULL,
    slot TEXT NOT NULL,
    value TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS facts_user_idx ON facts (user_id);
"""


def get_memory_conn():
    return get_conn("memory")


def init_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)


def reset_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS facts CASCADE")
    init_schema(conn)


def insert_fact(cur, user_id: str, session_id: int, slot: str, value: str, text: str) -> int:
    cur.execute(
        "INSERT INTO facts (user_id, session_id, slot, value, text) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (user_id, session_id, slot, value, text),
    )
    return cur.fetchone()[0]


def facts_for_user(cur, user_id: str) -> list[dict]:
    cur.execute("SELECT id, session_id, slot, value, text FROM facts WHERE user_id=%s", (user_id,))
    return [{"id": r[0], "session_id": r[1], "slot": r[2], "value": r[3], "text": r[4]} for r in cur.fetchall()]


def all_facts_unscoped(cur) -> list[dict]:
    """Used only by the isolation check's non-vacuousness probe (see
    tests/test_memory_isolation.py and measure.py): confirms that, without
    the user_id filter, other users' facts really would match, so a later
    zero-leak result under the filter is not vacuously true."""
    cur.execute("SELECT id, user_id, session_id, slot, value, text FROM facts")
    return [{"id": r[0], "user_id": r[1], "session_id": r[2], "slot": r[3], "value": r[4], "text": r[5]} for r in cur.fetchall()]
