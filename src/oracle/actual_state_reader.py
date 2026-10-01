"""ActualStateReader: reads the real, current field state directly out of
Postgres, the same database the environment services wrote to. It opens its own
psycopg2 connection (only importing src.config for connection constants, which
are data, not execution logic) rather than importing src.db, src.executor,
src.gateway, or src.environments, so that reading "what actually happened" never
goes through any code path the executor also uses to produce it.
"""

import psycopg2

from src import config


def _connect(schema: str):
    conn = psycopg2.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DB,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
    )
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
    return conn


def read_account(acc_id: str):
    conn = _connect("crm")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, tier, industry, deleted FROM accounts WHERE id=%s", (acc_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"name": row[0], "tier": row[1], "industry": row[2], "deleted": row[3]}


def read_contact(con_id: str):
    conn = _connect("crm")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT account_id, name, email, deleted FROM contacts WHERE id=%s", (con_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"account_id": row[0], "name": row[1], "email": row[2], "deleted": row[3]}


def read_opportunity(opp_id: str):
    conn = _connect("crm")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT account_id, stage, amount, deleted FROM opportunities WHERE id=%s", (opp_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"account_id": row[0], "stage": row[1], "amount": float(row[2]), "deleted": row[3]}


def read_ticket(tkt_id: str):
    conn = _connect("ticketing")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT subject, status, priority, assignee, close_reason FROM tickets WHERE id=%s",
                (tkt_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"subject": row[0], "status": row[1], "priority": row[2], "assignee": row[3], "close_reason": row[4]}


def read_product(prd_id: str):
    conn = _connect("inventory")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, category, active FROM products WHERE id=%s", (prd_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"name": row[0], "category": row[1], "active": row[2]}


def read_stock(product_id: str, warehouse: str):
    conn = _connect("inventory")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT quantity FROM stock WHERE product_id=%s AND warehouse=%s",
                (product_id, warehouse),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return row[0] if row else 0


def read_actual_state(expected_state: dict) -> dict:
    """Read real rows for exactly the entities the ReferenceSimulator's expected
    state mentions (so grading never depends on scanning the whole table)."""
    actual = {"accounts": {}, "contacts": {}, "opportunities": {}, "tickets": {}, "products": {}, "stock": {}}
    for acc_id in expected_state["accounts"]:
        actual["accounts"][acc_id] = read_account(acc_id)
    for con_id in expected_state["contacts"]:
        actual["contacts"][con_id] = read_contact(con_id)
    for opp_id in expected_state["opportunities"]:
        actual["opportunities"][opp_id] = read_opportunity(opp_id)
    for tkt_id in expected_state["tickets"]:
        actual["tickets"][tkt_id] = read_ticket(tkt_id)
    for prd_id in expected_state["products"]:
        actual["products"][prd_id] = read_product(prd_id)
    for (prd_id, wh) in expected_state["stock"]:
        actual["stock"][(prd_id, wh)] = read_stock(prd_id, wh)
    return actual
