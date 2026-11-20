"""The expected-state oracle for the finance-workflow extension: reads real
Postgres rows straight back out of `finance_ops` and compares the one field
each family's tool wrote against the Task's own expected value (computed by
tasks.py from the true seed data, before any mistake was injected). Mirrors
the top-level repository's oracle/executor split and the memory extension's
oracle.py; this module imports neither `src.finance.tools` nor `src.executor`,
`src.gateway`, `src.environments` (see tests/test_finance_oracle_independence.py).
"""

from __future__ import annotations

from src.finance.tasks import FinanceTask

_LOOKUP_SQL = {
    "invoice_three_way_match": ("invoices", "invoice_id", "status"),
    "expense_report_approval": ("expense_reports", "report_id", "status"),
    "vendor_master_update": ("vendors", "vendor_id", "bank_account"),
    "budget_transfer_posting": ("budget_transfers", "transfer_id", "to_cc"),
    "close_task_completion": ("close_tasks", "task_id", "evidence_doc_id"),
}


def read_actual_value(cur, task: FinanceTask):
    table, key_col, value_col = _LOOKUP_SQL[task.family]
    cur.execute(f"SELECT {value_col} FROM {table} WHERE {key_col}=%s", (task.lookup_id,))
    row = cur.fetchone()
    return row[0] if row else None


def grade(cur, task: FinanceTask) -> bool:
    actual = read_actual_value(cur, task)
    if isinstance(task.expected_value, float):
        return actual is not None and abs(float(actual) - task.expected_value) < 1e-6
    return actual == task.expected_value
