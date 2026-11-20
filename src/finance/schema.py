"""The finance-workflow extension's data model: Postgres schema `finance_ops`,
reusing `src.db.get_conn` the same way the three original environment services
and the memory extension do. Five tables are the "source of truth" an agent's
tool call reads from or writes to (invoices, expense_reports, vendors,
cost_centers, close_tasks); two more (purchase_orders/receipts and
evidence_registry) are fixed reference data a correct tool call is supposed to
look up and a wrong one is supposed to substitute, which is exactly the
injected-mistake mechanism src/finance/tasks.py uses.
"""

from __future__ import annotations

from src.db import get_conn

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id TEXT PRIMARY KEY,
    amount NUMERIC NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
    receipt_id TEXT PRIMARY KEY,
    amount NUMERIC NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    invoice_amount NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    variance_pct NUMERIC
);
CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    policy_cap NUMERIC NOT NULL
);
CREATE TABLE IF NOT EXISTS expense_reports (
    report_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id TEXT PRIMARY KEY,
    bank_account TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cost_centers (
    cc_id TEXT PRIMARY KEY,
    budget NUMERIC NOT NULL
);
CREATE TABLE IF NOT EXISTS budget_transfers (
    transfer_id TEXT PRIMARY KEY,
    from_cc TEXT NOT NULL,
    to_cc TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS evidence_registry (
    doc_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS close_tasks (
    task_id TEXT PRIMARY KEY,
    cost_center_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    evidence_doc_id TEXT
);
"""

_TABLES = (
    "purchase_orders",
    "receipts",
    "invoices",
    "employees",
    "expense_reports",
    "vendors",
    "cost_centers",
    "budget_transfers",
    "evidence_registry",
    "close_tasks",
)


def get_finance_conn():
    return get_conn("finance_ops")


def init_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)


def reset_schema(conn) -> None:
    with conn.cursor() as cur:
        for t in _TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    init_schema(conn)
