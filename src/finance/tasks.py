"""Builds the 420-task finance-workflow corpus: 84 tasks in each of 5 skill
families, 28 of each (1 in 3, the same injection rate the top-level
CRM/ticketing/inventory benchmark uses) with one argument deliberately
swapped for a wrong-but-plausible value before the tool call executes. The
swap is chosen, per family, to guarantee the tool's naive final write
disagrees with the task's own expected value; see tools.py's module
docstring for why the tool call itself still reports ok=True either way.

Each Task carries its own `expected_*` value, computed here from the true
seed data the task itself created, the same convention
`src/memory/tasks.py` uses for its four graded qualities. src/finance/oracle.py
never imports this module's sibling, src/finance/tools.py; it only reads
real Postgres rows and compares them to the Task's expected value.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

N_PER_FAMILY = 84
MISTAKE_EVERY_NTH = 3  # 1 in 3, 28 of 84 per family, 140 of 420 total


@dataclass
class FinanceTask:
    task_id: str
    family: str
    is_mistake: bool
    tool_args: dict
    expected_field: str
    expected_value: object
    lookup_id: str  # the row id the oracle reads back after the tool runs


def _seed_invoice_tasks(cur, rng: random.Random) -> list[FinanceTask]:
    tasks = []
    for i in range(N_PER_FAMILY):
        is_mistake = i % MISTAKE_EVERY_NTH == 0
        invoice_id = f"INV-{i:04d}"
        po_id, receipt_id = f"PO-{i:04d}", f"RCPT-{i:04d}"
        invoice_amount = round(rng.uniform(500.0, 20000.0), 2)
        # true po/receipt amounts within tolerance of the invoice amount, so the
        # honest, uncorrupted three-way match always approves
        true_po = round(invoice_amount * rng.uniform(0.995, 1.015), 2)
        true_receipt = round(invoice_amount * rng.uniform(0.995, 1.015), 2)
        cur.execute("INSERT INTO purchase_orders (po_id, amount) VALUES (%s, %s)", (po_id, true_po))
        cur.execute("INSERT INTO receipts (receipt_id, amount) VALUES (%s, %s)", (receipt_id, true_receipt))
        cur.execute(
            "INSERT INTO invoices (invoice_id, po_id, receipt_id, invoice_amount) VALUES (%s, %s, %s, %s)",
            (invoice_id, po_id, receipt_id, invoice_amount),
        )
        if is_mistake:
            # 10% above the invoice amount, well past the 2% tolerance either way
            po_amount_arg = round(invoice_amount * 1.10, 2)
            receipt_amount_arg = true_receipt
        else:
            po_amount_arg = true_po
            receipt_amount_arg = true_receipt
        tasks.append(
            FinanceTask(
                task_id=invoice_id,
                family="invoice_three_way_match",
                is_mistake=is_mistake,
                tool_args={"invoice_id": invoice_id, "po_amount": po_amount_arg, "receipt_amount": receipt_amount_arg},
                expected_field="status",
                expected_value="approved",  # the true po/receipt are always within tolerance
                lookup_id=invoice_id,
            )
        )
    return tasks


def _seed_expense_tasks(cur, rng: random.Random) -> list[FinanceTask]:
    tasks = []
    categories = {"travel": 3000.0, "meals": 150.0, "equipment": 2500.0}
    for i in range(N_PER_FAMILY):
        is_mistake = i % MISTAKE_EVERY_NTH == 0
        report_id, employee_id = f"EXP-{i:04d}", f"EMP-{i:04d}"
        category = list(categories)[i % 3]
        true_cap = categories[category]
        cur.execute(
            "INSERT INTO employees (employee_id, category, policy_cap) VALUES (%s, %s, %s)",
            (employee_id, category, true_cap),
        )
        amount = round(true_cap * rng.uniform(0.5, 0.95), 2)  # always under the true cap
        cur.execute(
            "INSERT INTO expense_reports (report_id, employee_id, amount) VALUES (%s, %s, %s)",
            (report_id, employee_id, amount),
        )
        policy_cap_arg = round(true_cap * 0.5, 2) if is_mistake else true_cap  # a wrong, much lower cap
        tasks.append(
            FinanceTask(
                task_id=report_id,
                family="expense_report_approval",
                is_mistake=is_mistake,
                tool_args={"report_id": report_id, "amount": amount, "policy_cap": policy_cap_arg},
                expected_field="status",
                expected_value="approved",  # amount is always under the true cap by construction
                lookup_id=report_id,
            )
        )
    return tasks


def _seed_vendor_tasks(cur, rng: random.Random) -> list[FinanceTask]:
    tasks = []
    for i in range(N_PER_FAMILY):
        is_mistake = i % MISTAKE_EVERY_NTH == 0
        vendor_id = f"VEND-{i:04d}"
        true_requested_account = f"ACCT-{i:06d}"
        wrong_account = f"ACCT-{(i + 41) % N_PER_FAMILY:06d}"  # another task's account, a plausible swap
        cur.execute(
            "INSERT INTO vendors (vendor_id, bank_account) VALUES (%s, %s)",
            (vendor_id, f"ACCT-OLD-{i:06d}"),
        )
        new_bank_account_arg = wrong_account if is_mistake else true_requested_account
        tasks.append(
            FinanceTask(
                task_id=vendor_id,
                family="vendor_master_update",
                is_mistake=is_mistake,
                tool_args={"vendor_id": vendor_id, "new_bank_account": new_bank_account_arg},
                expected_field="bank_account",
                expected_value=true_requested_account,
                lookup_id=vendor_id,
            )
        )
    return tasks


def _seed_transfer_tasks(cur, rng: random.Random) -> list[FinanceTask]:
    tasks = []
    for i in range(N_PER_FAMILY):
        is_mistake = i % MISTAKE_EVERY_NTH == 0
        transfer_id = f"XFER-{i:04d}"
        from_cc, true_to_cc = f"CC-FROM-{i:04d}", f"CC-TO-{i:04d}"
        wrong_to_cc = f"CC-TO-{(i + 17) % N_PER_FAMILY:04d}"  # another task's destination center
        amount = round(rng.uniform(1000.0, 50000.0), 2)
        cur.execute("INSERT INTO cost_centers (cc_id, budget) VALUES (%s, %s)", (from_cc, 1_000_000.0))
        cur.execute("INSERT INTO cost_centers (cc_id, budget) VALUES (%s, %s) ON CONFLICT DO NOTHING", (true_to_cc, 1_000_000.0))
        cur.execute("INSERT INTO cost_centers (cc_id, budget) VALUES (%s, %s) ON CONFLICT DO NOTHING", (wrong_to_cc, 1_000_000.0))
        cur.execute(
            "INSERT INTO budget_transfers (transfer_id, from_cc, to_cc, amount) VALUES (%s, %s, %s, %s)",
            (transfer_id, from_cc, true_to_cc, amount),
        )
        to_cc_arg = wrong_to_cc if is_mistake else true_to_cc
        tasks.append(
            FinanceTask(
                task_id=transfer_id,
                family="budget_transfer_posting",
                is_mistake=is_mistake,
                tool_args={"transfer_id": transfer_id, "from_cc": from_cc, "to_cc": to_cc_arg, "amount": amount},
                expected_field="to_cc",
                expected_value=true_to_cc,
                lookup_id=transfer_id,
            )
        )
    return tasks


def _seed_close_task_tasks(cur, rng: random.Random) -> list[FinanceTask]:
    tasks = []
    for i in range(N_PER_FAMILY):
        is_mistake = i % MISTAKE_EVERY_NTH == 0
        task_id, cc_id = f"CLOSE-{i:04d}", f"CC-{i:04d}"
        true_doc_id = f"DOC-{i:04d}"
        wrong_doc_id = f"DOC-{(i + 29) % N_PER_FAMILY:04d}"  # a real doc, for a different close task
        cur.execute("INSERT INTO close_tasks (task_id, cost_center_id) VALUES (%s, %s)", (task_id, cc_id))
        cur.execute("INSERT INTO evidence_registry (doc_id, task_id) VALUES (%s, %s)", (true_doc_id, task_id))
        evidence_doc_id_arg = wrong_doc_id if is_mistake else true_doc_id
        tasks.append(
            FinanceTask(
                task_id=task_id,
                family="close_task_completion",
                is_mistake=is_mistake,
                tool_args={"task_id": task_id, "evidence_doc_id": evidence_doc_id_arg},
                expected_field="evidence_doc_id",
                expected_value=true_doc_id,
                lookup_id=task_id,
            )
        )
    return tasks


_BUILDERS = (
    _seed_invoice_tasks,
    _seed_expense_tasks,
    _seed_vendor_tasks,
    _seed_transfer_tasks,
    _seed_close_task_tasks,
)


def build_corpus(cur, seed: int) -> list[FinanceTask]:
    rng = random.Random(seed)
    tasks: list[FinanceTask] = []
    for builder in _BUILDERS:
        tasks += builder(cur, rng)
    assert len(tasks) == 420, f"expected 420 finance tasks, built {len(tasks)}"
    assert sum(t.is_mistake for t in tasks) == 140, "expected 140 of 420 tasks (1 in 3) to carry an injected mistake"
    return tasks
