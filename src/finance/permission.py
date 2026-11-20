"""Role-scoped tool access for the finance-workflow extension: one role per
skill family, each granted exactly that family's single tool, and a 120-plan
adversarial suite (24 per role) that inserts one out-of-scope tool call into
an otherwise-legitimate single-step plan and confirms the scope check refuses
it before anything executes. Deliberately family-level, not field-level, the
same coarseness `src/permission/scope_checker.py` uses for the top-level
CRM/ticketing/inventory benchmark: the claim under test is that a plan
touching a tool outside the role's one family is refused outright.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.finance.tools import FAMILIES, TOOL_BY_FAMILY

TOOL_NAME_BY_FAMILY = {family: tool.__name__ for family, tool in TOOL_BY_FAMILY.items()}
FAMILY_BY_TOOL_NAME = {name: family for family, name in TOOL_NAME_BY_FAMILY.items()}


@dataclass(frozen=True)
class FinanceRole:
    name: str
    granted_family: str


ROLES = [FinanceRole(name=f"{family}_owner", granted_family=family) for family in FAMILIES]


@dataclass
class ScopeCheckResult:
    allowed: bool
    offending_tool: str = ""
    offending_family: str = ""
    reason: str = "allowed"


def check(tool_calls: list[str], role: FinanceRole) -> ScopeCheckResult:
    for tool_name in tool_calls:
        family = FAMILY_BY_TOOL_NAME.get(tool_name, "UNKNOWN")
        if family != role.granted_family:
            return ScopeCheckResult(
                allowed=False,
                offending_tool=tool_name,
                offending_family=family,
                reason=(
                    f"calls {tool_name!r} (family {family!r}), which role {role.name} "
                    f"is not granted (granted: {role.granted_family!r})"
                ),
            )
    return ScopeCheckResult(allowed=True)


N_PLANS_PER_ROLE = 24


def build_adversarial_suite() -> list[dict]:
    """24 plans per role x 5 roles = 120. Each plan is the role's own legitimate
    tool call plus exactly one out-of-scope call from a different family,
    alternated start/end so the offending step is not always in the same
    position."""
    suite = []
    other_families_by_role = {
        role.name: [f for f in FAMILIES if f != role.granted_family] for role in ROLES
    }
    for role in ROLES:
        own_tool = TOOL_NAME_BY_FAMILY[role.granted_family]
        others = other_families_by_role[role.name]
        for j in range(N_PLANS_PER_ROLE):
            offending_family = others[j % len(others)]
            offending_tool = TOOL_NAME_BY_FAMILY[offending_family]
            at_start = j % 2 == 0
            tool_calls = [offending_tool, own_tool] if at_start else [own_tool, offending_tool]
            suite.append(
                {
                    "role": role,
                    "tool_calls": tool_calls,
                    "expected_offending_tool": offending_tool,
                    "expected_offending_family": offending_family,
                }
            )
    assert len(suite) == 120
    return suite
