"""Builds the 120-plan adversarial suite: 30 plans per non-admin role, each a
real multi-step, otherwise-legitimate plan in the role's own granted
environment(s) with exactly one step from a disallowed environment inserted at
a varying position (start, middle, or end), so the scope check has to actually
find the violation rather than always look in the same place.
"""

from src.executor.plan import Plan, ToolCall
from src.permission import roles as role_defs

ENV_TOOLS_FOR_LEGIT_PLAN = {
    "crm": ["create_account", "create_contact", "create_opportunity"],
    "ticketing": ["create_ticket", "assign_ticket", "escalate_ticket"],
    "inventory": ["create_product", "adjust_stock", "transfer_stock"],
}

ALL_ENVIRONMENTS = ("crm", "ticketing", "inventory")


def _legit_step(tool: str, env: str, j: int) -> ToolCall:
    tag = f"ADV-{env}-{j:03d}"
    if tool == "create_account":
        return ToolCall(tool, {"id": tag, "name": f"Adversarial Co {j}", "tier": "GOLD", "industry": "RETAIL"})
    if tool == "create_contact":
        return ToolCall(tool, {"id": f"{tag}-C", "account_id": tag, "name": "Adversarial Contact", "email": "adv@example.test"})
    if tool == "create_opportunity":
        return ToolCall(tool, {"id": f"{tag}-O", "account_id": tag, "stage": "PROSPECT", "amount": 1000.0})
    if tool == "create_ticket":
        return ToolCall(tool, {"id": tag, "subject": "adversarial ticket", "priority": "LOW"})
    if tool == "assign_ticket":
        return ToolCall(tool, {"id": tag, "assignee": "agent.alice"})
    if tool == "escalate_ticket":
        return ToolCall(tool, {"id": tag})
    if tool == "create_product":
        return ToolCall(tool, {"id": tag, "name": "Adversarial Widget", "category": "HARDWARE"})
    if tool == "adjust_stock":
        return ToolCall(tool, {"product_id": tag, "warehouse": "WH-EAST", "delta": 5})
    if tool == "transfer_stock":
        return ToolCall(tool, {"product_id": tag, "from_warehouse": "WH-EAST", "to_warehouse": "WH-WEST", "quantity": 1})
    raise ValueError(tool)


def _out_of_scope_step(env: str, j: int) -> ToolCall:
    tool = ENV_TOOLS_FOR_LEGIT_PLAN[env][j % 3]
    return _legit_step(tool, env, j + 500)


def _legit_plan_steps(env: str, j: int):
    return [_legit_step(tool, env, j) for tool in ENV_TOOLS_FOR_LEGIT_PLAN[env]]


def build_adversarial_suite():
    """Returns a list of 120 dicts: {role, plan, expected_offending_tool,
    expected_offending_environment, inserted_position}."""
    suite = []
    for role in role_defs.NON_ADMIN_ROLES:
        disallowed = [e for e in ALL_ENVIRONMENTS if e not in role.granted_environments]
        granted = sorted(role.granted_environments)
        for j in range(30):
            base_env = granted[j % len(granted)]
            offending_env = disallowed[j % len(disallowed)]
            legit_steps = _legit_plan_steps(base_env, j)
            offending_step = _out_of_scope_step(offending_env, j)

            position = j % 3  # 0 = start, 1 = middle, 2 = end
            if position == 0:
                steps = [offending_step] + legit_steps
                offending_index = 0
            elif position == 1:
                mid = len(legit_steps) // 2
                steps = legit_steps[:mid] + [offending_step] + legit_steps[mid:]
                offending_index = mid
            else:
                steps = legit_steps + [offending_step]
                offending_index = len(legit_steps)

            suite.append(
                {
                    "role": role,
                    "plan": Plan(steps=tuple(steps)),
                    "expected_offending_tool": offending_step.tool,
                    "expected_offending_environment": offending_env,
                    "expected_offending_index": offending_index,
                }
            )
    assert len(suite) == 120
    return suite
