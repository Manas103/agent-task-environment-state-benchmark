"""Generates the 420-task corpus: 6 templates (2 per work environment) x 70
instances each. Every third task (global index % 3 == 0, 140 of 420) gets one
injected mistake: a single tool-call argument is swapped for a different, still
valid value, so the executed plan's steps all still report success. The
reference plan (the one the oracle grades against) always uses the
instruction's true intended values; it is never executed.
"""

from dataclasses import dataclass

from src.executor.plan import Plan, ToolCall
from src.tasks import value_pools as vp


@dataclass
class Task:
    id: str
    environment: str
    template: str
    instruction: str
    reference_plan: Plan
    executed_plan: Plan
    has_mistake: bool
    mistake_note: str


def _crm_a(i: int, global_idx: int, mistake: bool) -> Task:
    acc = f"ACC-A-{i:04d}"
    con = f"CON-A-{i:04d}"
    opp = f"OPP-A-{i:04d}"
    name = vp.company_name(i)
    tier = vp.TIERS[i % len(vp.TIERS)]
    industry = vp.INDUSTRIES[i % len(vp.INDUSTRIES)]
    contact = vp.contact_name(i)
    stage = vp.STAGES[i % len(vp.STAGES)]
    amount = float(1000 + (i % 50) * 250)

    instruction = (
        f"Create account {name} in the {industry} industry at tier {tier}, "
        f"add contact {contact} for that account, and log an opportunity at "
        f"stage {stage} worth {amount:.2f}."
    )
    reference = Plan(
        steps=(
            ToolCall("create_account", {"id": acc, "name": name, "tier": tier, "industry": industry}),
            ToolCall("create_contact", {"id": con, "account_id": acc, "name": contact, "email": f"{con.lower()}@example.test"}),
            ToolCall("create_opportunity", {"id": opp, "account_id": acc, "stage": stage, "amount": amount}),
        )
    )
    executed_stage = vp.other_than(vp.STAGES, stage) if mistake else stage
    executed = Plan(
        steps=(
            ToolCall("create_account", {"id": acc, "name": name, "tier": tier, "industry": industry}),
            ToolCall("create_contact", {"id": con, "account_id": acc, "name": contact, "email": f"{con.lower()}@example.test"}),
            ToolCall("create_opportunity", {"id": opp, "account_id": acc, "stage": executed_stage, "amount": amount}),
        )
    )
    note = f"opportunity stage set to {executed_stage} instead of {stage}" if mistake else ""
    return Task(f"T{global_idx:04d}-crm-a", "crm", "crm_a", instruction, reference, executed, mistake, note)


def _crm_b(i: int, global_idx: int, mistake: bool) -> Task:
    acc = f"ACC-B-{i:04d}"
    con = f"CON-B-{i:04d}"
    name = vp.company_name(i + 1000)
    tier1 = vp.TIERS[i % len(vp.TIERS)]
    tier2 = vp.other_than(vp.TIERS, tier1)
    industry = vp.INDUSTRIES[(i + 1) % len(vp.INDUSTRIES)]
    contact = vp.contact_name(i + 1000)

    instruction = (
        f"Create account {name} at tier {tier1}, then correct its tier to {tier2}, "
        f"and delete contact {contact} for that account."
    )
    reference = Plan(
        steps=(
            ToolCall("create_account", {"id": acc, "name": name, "tier": tier1, "industry": industry}),
            ToolCall("create_contact", {"id": con, "account_id": acc, "name": contact, "email": f"{con.lower()}@example.test"}),
            ToolCall("update_account_tier", {"id": acc, "tier": tier2}),
            ToolCall("delete_contact", {"id": con}),
        )
    )
    executed_tier2 = vp.other_than(vp.TIERS, tier2) if mistake else tier2
    executed = Plan(
        steps=(
            ToolCall("create_account", {"id": acc, "name": name, "tier": tier1, "industry": industry}),
            ToolCall("create_contact", {"id": con, "account_id": acc, "name": contact, "email": f"{con.lower()}@example.test"}),
            ToolCall("update_account_tier", {"id": acc, "tier": executed_tier2}),
            ToolCall("delete_contact", {"id": con}),
        )
    )
    note = f"final tier set to {executed_tier2} instead of {tier2}" if mistake else ""
    return Task(f"T{global_idx:04d}-crm-b", "crm", "crm_b", instruction, reference, executed, mistake, note)


def _ticketing_a(i: int, global_idx: int, mistake: bool) -> Task:
    tkt = f"TKT-A-{i:04d}"
    subject = vp.ticket_subject(i)
    priority = vp.PRIORITIES[i % 3]  # never start at CRITICAL so escalate always changes it
    assignee = vp.ASSIGNEES[i % len(vp.ASSIGNEES)]

    instruction = (
        f"Open ticket '{subject}' at priority {priority}, assign it to {assignee}, "
        f"then escalate it one level."
    )
    reference = Plan(
        steps=(
            ToolCall("create_ticket", {"id": tkt, "subject": subject, "priority": priority}),
            ToolCall("assign_ticket", {"id": tkt, "assignee": assignee}),
            ToolCall("escalate_ticket", {"id": tkt}),
        )
    )
    executed_assignee = vp.other_than(vp.ASSIGNEES, assignee) if mistake else assignee
    executed = Plan(
        steps=(
            ToolCall("create_ticket", {"id": tkt, "subject": subject, "priority": priority}),
            ToolCall("assign_ticket", {"id": tkt, "assignee": executed_assignee}),
            ToolCall("escalate_ticket", {"id": tkt}),
        )
    )
    note = f"assigned to {executed_assignee} instead of {assignee}" if mistake else ""
    return Task(f"T{global_idx:04d}-tkt-a", "ticketing", "ticketing_a", instruction, reference, executed, mistake, note)


def _ticketing_b(i: int, global_idx: int, mistake: bool) -> Task:
    tkt = f"TKT-B-{i:04d}"
    subject = vp.ticket_subject(i + 500)
    assignee = vp.ASSIGNEES[(i + 1) % len(vp.ASSIGNEES)]
    priority = vp.PRIORITIES[(i + 2) % len(vp.PRIORITIES)]
    reason = vp.CLOSE_REASONS[i % len(vp.CLOSE_REASONS)]

    instruction = (
        f"Open ticket '{subject}' at priority {priority}, assign it to {assignee}, "
        f"then close it with reason {reason}."
    )
    reference = Plan(
        steps=(
            ToolCall("create_ticket", {"id": tkt, "subject": subject, "priority": priority}),
            ToolCall("assign_ticket", {"id": tkt, "assignee": assignee}),
            ToolCall("close_ticket", {"id": tkt, "close_reason": reason}),
        )
    )
    executed_reason = vp.other_than(vp.CLOSE_REASONS, reason) if mistake else reason
    executed = Plan(
        steps=(
            ToolCall("create_ticket", {"id": tkt, "subject": subject, "priority": priority}),
            ToolCall("assign_ticket", {"id": tkt, "assignee": assignee}),
            ToolCall("close_ticket", {"id": tkt, "close_reason": executed_reason}),
        )
    )
    note = f"closed with reason {executed_reason} instead of {reason}" if mistake else ""
    return Task(f"T{global_idx:04d}-tkt-b", "ticketing", "ticketing_b", instruction, reference, executed, mistake, note)


def _inventory_a(i: int, global_idx: int, mistake: bool) -> Task:
    prd = f"PRD-A-{i:04d}"
    name = vp.product_name(i)
    category = vp.CATEGORIES[i % len(vp.CATEGORIES)]
    wh = vp.WAREHOUSES[i % len(vp.WAREHOUSES)]
    qty = 10 + (i % 40)

    instruction = f"Create product {name} in category {category}, stock {qty} units at {wh}."
    reference = Plan(
        steps=(
            ToolCall("create_product", {"id": prd, "name": name, "category": category}),
            ToolCall("adjust_stock", {"product_id": prd, "warehouse": wh, "delta": qty}),
        )
    )
    executed_wh = vp.other_than(vp.WAREHOUSES, wh) if mistake else wh
    executed = Plan(
        steps=(
            ToolCall("create_product", {"id": prd, "name": name, "category": category}),
            ToolCall("adjust_stock", {"product_id": prd, "warehouse": executed_wh, "delta": qty}),
        )
    )
    note = f"stock placed at {executed_wh} instead of {wh}" if mistake else ""
    return Task(f"T{global_idx:04d}-inv-a", "inventory", "inventory_a", instruction, reference, executed, mistake, note)


def _inventory_b(i: int, global_idx: int, mistake: bool) -> Task:
    prd = f"PRD-B-{i:04d}"
    name = vp.product_name(i + 2000)
    category = vp.CATEGORIES[(i + 1) % len(vp.CATEGORIES)]
    wh1 = vp.WAREHOUSES[i % len(vp.WAREHOUSES)]
    wh2 = vp.other_than(vp.WAREHOUSES, wh1)
    qty = 20 + (i % 30)
    move_qty = 1 + (i % (qty - 1)) if qty > 1 else 1

    instruction = (
        f"Create product {name}, stock {qty} units at {wh1}, then transfer "
        f"{move_qty} units to {wh2}."
    )
    reference = Plan(
        steps=(
            ToolCall("create_product", {"id": prd, "name": name, "category": category}),
            ToolCall("adjust_stock", {"product_id": prd, "warehouse": wh1, "delta": qty}),
            ToolCall("transfer_stock", {"product_id": prd, "from_warehouse": wh1, "to_warehouse": wh2, "quantity": move_qty}),
        )
    )
    executed_wh2 = vp.other_than(vp.WAREHOUSES, wh2) if mistake else wh2
    executed = Plan(
        steps=(
            ToolCall("create_product", {"id": prd, "name": name, "category": category}),
            ToolCall("adjust_stock", {"product_id": prd, "warehouse": wh1, "delta": qty}),
            ToolCall("transfer_stock", {"product_id": prd, "from_warehouse": wh1, "to_warehouse": executed_wh2, "quantity": move_qty}),
        )
    )
    note = f"transferred to {executed_wh2} instead of {wh2}" if mistake else ""
    return Task(f"T{global_idx:04d}-inv-b", "inventory", "inventory_b", instruction, reference, executed, mistake, note)


TEMPLATES = [_crm_a, _crm_b, _ticketing_a, _ticketing_b, _inventory_a, _inventory_b]
INSTANCES_PER_TEMPLATE = 70


def generate_all():
    """Returns the 420 tasks in a fixed, deterministic order: instance index outer
    loop, template inner loop, so mistake injection (every third by global index)
    spreads evenly across all six templates rather than clumping in one."""
    tasks = []
    global_idx = 0
    for i in range(INSTANCES_PER_TEMPLATE):
        for template in TEMPLATES:
            mistake = (global_idx % 3 == 0)
            tasks.append(template(i, global_idx, mistake))
            global_idx += 1
    assert len(tasks) == 420
    return tasks
