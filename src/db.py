"""Shared Postgres connection helper for the three environment services (crm,
ticketing, inventory). This module is infrastructure plumbing used only on the
executor side (the environment services and the gateway); src/oracle never imports
it, see src/oracle/actual_state_reader.py for the oracle's own, separate connection
code.
"""

import psycopg2

from src import config


def get_conn(schema: str):
    """Return a new psycopg2 connection with search_path pinned to one schema."""
    conn = psycopg2.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DB,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        cur.execute(f"SET search_path TO {schema}")
    return conn


CRM_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL,
    industry TEXT NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);
"""

TICKETING_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    assignee TEXT,
    close_reason TEXT,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);
"""

INVENTORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS stock (
    product_id TEXT NOT NULL,
    warehouse TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (product_id, warehouse)
);
"""

SCHEMA_SQL = {
    "crm": CRM_SCHEMA_SQL,
    "ticketing": TICKETING_SCHEMA_SQL,
    "inventory": INVENTORY_SCHEMA_SQL,
}


def init_schema(schema: str):
    conn = get_conn(schema)
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL[schema])
    conn.close()


def reset_schema(schema: str):
    """Drop and recreate one environment's tables. Used between benchmark runs so
    task ids generated fresh each run never collide with a previous run's rows."""
    conn = get_conn(schema)
    table_names = {
        "crm": ["accounts", "contacts", "opportunities"],
        "ticketing": ["tickets"],
        "inventory": ["products", "stock"],
    }[schema]
    with conn.cursor() as cur:
        for t in table_names:
            cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    conn.close()
    init_schema(schema)
