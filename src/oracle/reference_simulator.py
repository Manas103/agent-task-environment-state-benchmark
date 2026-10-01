"""ReferenceSimulator: an independent, from-scratch, in-memory interpreter of a
Plan's intended effect on final environment state. It shares no code with
src.executor, src.gateway, or src.environments (see tests/test_oracle_independence.py
for the mechanical import check): it does not call the gateway, does not touch
Postgres, and re-implements its own understanding of what each of the 13 tools
does, independently of the environment services that actually perform the writes.

It is always run over a task's reference_plan (the correct plan, which the
executor never runs), never over the executed_plan, which is why it still reports
the right answer even when the executor was handed a plan with an injected
mistake: the whole point of the oracle is to know what *should* have happened and
then separately check, in ActualStateReader, what *actually* happened.
"""

PRIORITY_LADDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _blank_state():
    return {
        "accounts": {},
        "contacts": {},
        "opportunities": {},
        "tickets": {},
        "products": {},
        "stock": {},  # key: (product_id, warehouse) -> quantity
    }


def simulate(plan) -> dict:
    """Walk a Plan's steps with this module's own switch-per-tool logic and
    return the expected final state, keyed by table name."""
    state = _blank_state()

    for call in plan.steps:
        tool = call.tool
        a = call.args

        if tool == "create_account":
            state["accounts"][a["id"]] = {
                "name": a["name"],
                "tier": a["tier"],
                "industry": a["industry"],
                "deleted": False,
            }
        elif tool == "update_account_tier":
            if a["id"] in state["accounts"]:
                state["accounts"][a["id"]]["tier"] = a["tier"]
        elif tool == "create_contact":
            state["contacts"][a["id"]] = {
                "account_id": a["account_id"],
                "name": a["name"],
                "email": a["email"],
                "deleted": False,
            }
        elif tool == "delete_contact":
            if a["id"] in state["contacts"]:
                state["contacts"][a["id"]]["deleted"] = True
        elif tool == "create_opportunity":
            state["opportunities"][a["id"]] = {
                "account_id": a["account_id"],
                "stage": a["stage"],
                "amount": float(a["amount"]),
                "deleted": False,
            }
        elif tool == "create_ticket":
            state["tickets"][a["id"]] = {
                "subject": a["subject"],
                "status": "OPEN",
                "priority": a["priority"],
                "assignee": None,
                "close_reason": None,
            }
        elif tool == "assign_ticket":
            if a["id"] in state["tickets"]:
                state["tickets"][a["id"]]["assignee"] = a["assignee"]
                state["tickets"][a["id"]]["status"] = "ASSIGNED"
        elif tool == "escalate_ticket":
            t = state["tickets"].get(a["id"])
            if t is not None:
                idx = PRIORITY_LADDER.index(t["priority"]) if t["priority"] in PRIORITY_LADDER else 0
                t["priority"] = PRIORITY_LADDER[min(idx + 1, len(PRIORITY_LADDER) - 1)]
        elif tool == "close_ticket":
            if a["id"] in state["tickets"]:
                state["tickets"][a["id"]]["status"] = "CLOSED"
                state["tickets"][a["id"]]["close_reason"] = a["close_reason"]
        elif tool == "create_product":
            state["products"][a["id"]] = {
                "name": a["name"],
                "category": a["category"],
                "active": True,
            }
        elif tool == "adjust_stock":
            key = (a["product_id"], a["warehouse"])
            state["stock"][key] = state["stock"].get(key, 0) + int(a["delta"])
        elif tool == "transfer_stock":
            from_key = (a["product_id"], a["from_warehouse"])
            to_key = (a["product_id"], a["to_warehouse"])
            state["stock"][from_key] = state["stock"].get(from_key, 0) - int(a["quantity"])
            state["stock"][to_key] = state["stock"].get(to_key, 0) + int(a["quantity"])
        elif tool == "retire_product":
            if a["id"] in state["products"]:
                state["products"][a["id"]]["active"] = False
        else:
            raise ValueError(f"ReferenceSimulator does not recognize tool: {tool}")

    return state
