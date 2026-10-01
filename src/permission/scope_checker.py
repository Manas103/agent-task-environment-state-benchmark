"""ScopeChecker: refuses a whole plan the moment any step's tool touches an
environment outside a role's granted set, before any step executes. This is the
pre-execution scope-check gate the 120-plan adversarial suite exercises.
"""

from dataclasses import dataclass

from src import config


@dataclass
class ScopeCheckResult:
    allowed: bool
    offending_step_index: int = -1
    offending_tool: str = ""
    offending_environment: str = ""
    reason: str = "allowed"


def check(plan, role) -> ScopeCheckResult:
    for idx, call in enumerate(plan.steps):
        if call.tool not in config.TOOL_CATALOG:
            return ScopeCheckResult(
                allowed=False,
                offending_step_index=idx,
                offending_tool=call.tool,
                offending_environment="UNKNOWN",
                reason=f"step {idx} uses unrecognized tool {call.tool!r}; refusing rather than guessing",
            )
        environment, _, _ = config.TOOL_CATALOG[call.tool]
        if environment not in role.granted_environments:
            return ScopeCheckResult(
                allowed=False,
                offending_step_index=idx,
                offending_tool=call.tool,
                offending_environment=environment,
                reason=(
                    f"step {idx} calls {call.tool!r} in environment {environment!r}, "
                    f"which role {role.name} is not granted (granted: {sorted(role.granted_environments)})"
                ),
            )
    return ScopeCheckResult(allowed=True)
