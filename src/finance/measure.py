"""Orchestrates the finance-workflow extension's measurement: builds the
420-task corpus (84 per family, 140 with one injected argument swap), runs
each task's tool call for real against Postgres, grades it with both the
transcript-only judge and the expected-state oracle, and separately runs the
120-plan adversarial scope-refusal suite. Mirrors src/memory/measure.py's
shape, applied to the finance_ops schema instead of the fact store.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.finance import permission, schema
from src.finance.judge import judge_pass
from src.finance.oracle import grade
from src.finance.tasks import build_corpus
from src.finance.tools import FAMILIES, TOOL_BY_FAMILY


def run_benchmark(seed: int = 2026) -> dict:
    conn = schema.get_finance_conn()
    conn.autocommit = True
    try:
        schema.reset_schema(conn)
        with conn.cursor() as cur:
            tasks = build_corpus(cur, seed=seed)

        per_family = {f: {"total": 0, "oracle_pass": 0, "judge_pass": 0, "mistakes": 0, "mistakes_caught": 0} for f in FAMILIES}
        with conn.cursor() as cur:
            for task in tasks:
                tool = TOOL_BY_FAMILY[task.family]
                result = tool(cur, **task.tool_args)
                oracle_ok = grade(cur, task)
                judge_ok = judge_pass(result)
                stats = per_family[task.family]
                stats["total"] += 1
                stats["oracle_pass"] += int(oracle_ok)
                stats["judge_pass"] += int(judge_ok)
                if task.is_mistake:
                    stats["mistakes"] += 1
                    stats["mistakes_caught"] += int(not oracle_ok)
    finally:
        conn.close()

    total = sum(v["total"] for v in per_family.values())
    oracle_pass = sum(v["oracle_pass"] for v in per_family.values())
    judge_pass_total = sum(v["judge_pass"] for v in per_family.values())
    mistakes = sum(v["mistakes"] for v in per_family.values())
    mistakes_caught = sum(v["mistakes_caught"] for v in per_family.values())

    return {
        "total_tasks": total,
        "per_family": {
            f: {
                **v,
                "oracle_pass_pct": round(100 * v["oracle_pass"] / v["total"], 2),
                "judge_pass_pct": round(100 * v["judge_pass"] / v["total"], 2),
            }
            for f, v in per_family.items()
        },
        "overall": {
            "oracle_pass_pct": round(100 * oracle_pass / total, 2),
            "judge_pass_pct": round(100 * judge_pass_total / total, 2),
            "overcredit_gap_points": round(100 * judge_pass_total / total - 100 * oracle_pass / total, 2),
        },
        "mistakes_injected": mistakes,
        "mistakes_caught_by_oracle": mistakes_caught,
    }


def run_adversarial_suite() -> dict:
    suite = permission.build_adversarial_suite()
    refused = 0
    allowed_through = []
    for case in suite:
        result = permission.check(case["tool_calls"], case["role"])
        if not result.allowed:
            refused += 1
            assert result.offending_tool == case["expected_offending_tool"]
            assert result.offending_family == case["expected_offending_family"]
        else:
            allowed_through.append(case)
    return {"total_plans": len(suite), "refused": refused, "allowed_through": len(allowed_through)}


def main(docs_dir: Path) -> dict:
    docs_dir.mkdir(parents=True, exist_ok=True)

    benchmark = run_benchmark()
    adversarial = run_adversarial_suite()

    report = {"benchmark": benchmark, "adversarial": adversarial}
    (docs_dir / "finance_measure_report.json").write_text(json.dumps(report, indent=2))

    lines = [
        f"total tasks: {benchmark['total_tasks']}",
        f"mistakes injected: {benchmark['mistakes_injected']}",
        f"mistakes caught by oracle: {benchmark['mistakes_caught_by_oracle']}/{benchmark['mistakes_injected']}",
        "",
        "per-family oracle vs judge pass rate:",
    ]
    for f, v in benchmark["per_family"].items():
        lines.append(
            f"  {f:<26} oracle {v['oracle_pass']}/{v['total']} ({v['oracle_pass_pct']}%)"
            f"  judge {v['judge_pass']}/{v['total']} ({v['judge_pass_pct']}%)"
        )
    lines += [
        "",
        f"overall oracle pass: {benchmark['overall']['oracle_pass_pct']}%",
        f"overall judge pass:  {benchmark['overall']['judge_pass_pct']}%",
        f"overcredit gap: {benchmark['overall']['overcredit_gap_points']} points",
        "",
        f"adversarial scope-refusal plans: {adversarial['total_plans']}",
        f"refused: {adversarial['refused']}",
        f"allowed through (should be 0): {adversarial['allowed_through']}",
    ]
    (docs_dir / "finance_benchmark_output.txt").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    import sys

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs")
    print(json.dumps(main(out_dir), indent=2))
