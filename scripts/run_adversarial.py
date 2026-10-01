"""Runs the 120-plan adversarial out-of-scope suite through ScopeChecker.check
and verifies every single one is refused before any tool executes. No
environment process or gateway is started for this run at all: the scope check
is a pure, in-memory function over a Plan and a Role, and since nothing is
listening on any port while this runs, any plan that was wrongly allowed through
to an executor call would fail loudly with a connection error rather than
silently succeed, which would make a bug here impossible to miss.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.permission import scope_checker
from src.permission.adversarial_generator import build_adversarial_suite


def main():
    suite = build_adversarial_suite()
    refused = 0
    wrong_step = 0
    allowed_through = []

    lines = [f"agent-task-environment-state-benchmark: adversarial scope-refusal suite ({len(suite)} plans)"]

    for entry in suite:
        result = scope_checker.check(entry["plan"], entry["role"])
        if result.allowed:
            allowed_through.append(entry)
            continue
        refused += 1
        if result.offending_step_index != entry["expected_offending_index"] or result.offending_tool != entry["expected_offending_tool"]:
            wrong_step += 1
            lines.append(
                f"  MISNAMED: role={entry['role'].name} expected step {entry['expected_offending_index']} "
                f"tool={entry['expected_offending_tool']!r}, got step {result.offending_step_index} tool={result.offending_tool!r}"
            )

    lines.append(f"refused: {refused}/{len(suite)}")
    lines.append(f"allowed through (should be 0): {len(allowed_through)}")
    lines.append(f"refused but named the wrong offending step/tool (should be 0): {wrong_step}")
    for entry in allowed_through:
        lines.append(f"  ALLOWED THROUGH: role={entry['role'].name} expected offending tool={entry['expected_offending_tool']}")

    by_role = {}
    for entry in suite:
        by_role.setdefault(entry["role"].name, 0)
        by_role[entry["role"].name] += 1
    lines.append(f"plans per role: {by_role}")

    out_text = "\n".join(lines)
    print(out_text)

    docs_dir = Path(__file__).resolve().parents[1] / "docs"
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / "scope_refusal_output.txt").write_text(out_text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
