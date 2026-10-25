"""Orchestrates the 300-task silicon-design benchmark measurement and writes docs/silicon_*.

Usage: PYTHONPATH=src python -m silicon.measure docs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .judge import judge_passes
from .tasks import FAMILIES, N_PER_FAMILY, generate_all_tasks


def main(docs_dir: Path) -> dict:
    docs_dir.mkdir(parents=True, exist_ok=True)
    tasks = generate_all_tasks()

    oracle_pass = sum(1 for t in tasks if t.oracle_result)
    judge_pass = sum(1 for t in tasks if judge_passes(t))
    gap = (judge_pass - oracle_pass) / len(tasks) * 100

    per_family = {}
    for fam in FAMILIES:
        fam_tasks = [t for t in tasks if t.family == fam]
        fam_oracle = sum(1 for t in fam_tasks if t.oracle_result)
        fam_judge = sum(1 for t in fam_tasks if judge_passes(t))
        per_family[fam] = {
            "n": len(fam_tasks),
            "oracle_pass": fam_oracle,
            "judge_pass": fam_judge,
            "n_wrong_injected": sum(1 for t in fam_tasks if t.is_wrong),
        }

    report = {
        "n_tasks": len(tasks),
        "n_families": len(FAMILIES),
        "n_per_family": N_PER_FAMILY,
        "oracle_pass": oracle_pass,
        "oracle_pass_rate": oracle_pass / len(tasks),
        "judge_pass": judge_pass,
        "judge_pass_rate": judge_pass / len(tasks),
        "overcredit_gap_points": round(gap, 2),
        "per_family": per_family,
    }

    (docs_dir / "silicon_measure_report.json").write_text(json.dumps(report, indent=2))
    per_task = [
        {"task_id": t.task_id, "family": t.family, "is_wrong": t.is_wrong,
         "oracle_result": t.oracle_result, "judge_result": judge_passes(t)}
        for t in tasks
    ]
    (docs_dir / "silicon_per_task.json").write_text(json.dumps(per_task, indent=2))

    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    docs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs")
    main(docs)
