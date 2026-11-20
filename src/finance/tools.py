"""The five finance-workflow tools under test, one per skill family. Each tool
is deliberately naive about the arguments it is handed: it trusts whatever
po_amount, policy_cap, bank_account, cost-center id or evidence_doc_id the
caller passes and writes the resulting state, the same "a wrong argument
value never makes the call fail" convention this repository's CRM/ticketing/
inventory tools use (see tools.py there, e.g. update_account_tier). This is
what lets a value-swap mistake slip past a transcript-only judge that only
checks ok=True while still being catchable by an oracle that recomputes the
expected value from scratch (src/finance/oracle.py).

None of this module is imported by src/finance/oracle.py; see
tests/test_finance_oracle_independence.py.
"""

from __future__ import annotations

MATCH_TOLERANCE_PCT = 2.0


def match_invoice(cur, invoice_id: str, po_amount: float, receipt_amount: float) -> dict:
    cur.execute("SELECT invoice_amount FROM invoices WHERE invoice_id=%s", (invoice_id,))
    row = cur.fetchone()
    invoice_amount = float(row[0])
    worst_discrepancy = max(abs(invoice_amount - po_amount), abs(invoice_amount - receipt_amount))
    variance_pct = 100.0 * worst_discrepancy / invoice_amount if invoice_amount else 0.0
    status = "approved" if variance_pct <= MATCH_TOLERANCE_PCT else "flagged"
    cur.execute(
        "UPDATE invoices SET status=%s, variance_pct=%s WHERE invoice_id=%s",
        (status, variance_pct, invoice_id),
    )
    return {"ok": True, "status": status, "variance_pct": variance_pct}


def approve_expense_report(cur, report_id: str, amount: float, policy_cap: float) -> dict:
    status = "approved" if amount <= policy_cap else "rejected"
    cur.execute("UPDATE expense_reports SET status=%s WHERE report_id=%s", (status, report_id))
    return {"ok": True, "status": status}


def update_vendor_bank_details(cur, vendor_id: str, new_bank_account: str) -> dict:
    cur.execute("UPDATE vendors SET bank_account=%s WHERE vendor_id=%s", (new_bank_account, vendor_id))
    return {"ok": True, "bank_account": new_bank_account}


def post_budget_transfer(cur, transfer_id: str, from_cc: str, to_cc: str, amount: float) -> dict:
    cur.execute("UPDATE cost_centers SET budget = budget - %s WHERE cc_id=%s", (amount, from_cc))
    cur.execute("UPDATE cost_centers SET budget = budget + %s WHERE cc_id=%s", (amount, to_cc))
    cur.execute(
        "UPDATE budget_transfers SET from_cc=%s, to_cc=%s, amount=%s, status='posted' WHERE transfer_id=%s",
        (from_cc, to_cc, amount, transfer_id),
    )
    return {"ok": True, "status": "posted"}


def complete_close_task(cur, task_id: str, evidence_doc_id: str) -> dict:
    # Deliberately naive: accepts whatever evidence_doc_id it is handed and marks the
    # task complete, the same way a real tool only checks "was a document attached"
    # and leaves "is it the right document" to a downstream review, which is exactly
    # the gap the oracle (src/finance/oracle.py) is built to catch.
    cur.execute(
        "UPDATE close_tasks SET status='complete', evidence_doc_id=%s WHERE task_id=%s",
        (evidence_doc_id, task_id),
    )
    return {"ok": True, "status": "complete"}


TOOL_BY_FAMILY = {
    "invoice_three_way_match": match_invoice,
    "expense_report_approval": approve_expense_report,
    "vendor_master_update": update_vendor_bank_details,
    "budget_transfer_posting": post_budget_transfer,
    "close_task_completion": complete_close_task,
}

FAMILIES = tuple(TOOL_BY_FAMILY)

assert len(FAMILIES) == 5, "the resume claims exactly 5 skill families"
