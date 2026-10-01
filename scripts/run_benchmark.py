"""The main measurement run: resets the three environment schemas, starts the
three environment processes plus the gateway as real local subprocesses,
generates and actually executes 420 multi-step task trajectories through the
gateway, grades every one of them with both the real expected-state oracle and
the deterministic transcript-only judge, and writes the raw summary to
docs/benchmark_output.txt.

Usage: python scripts/run_benchmark.py [--reset-db]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import server_manager
from src import db
from src.executor.executor import PlanExecutor
from src.judge.deterministic_judge import DeterministicLocalJudge
from src.oracle import oracle_interpreter
from src.tasks.task_generator import generate_all


def main():
    reset = "--reset-db" in sys.argv

    print("Resetting environment schemas..." if reset else "Ensuring environment schemas exist...")
    for schema in ("crm", "ticketing", "inventory"):
        if reset:
            db.reset_schema(schema)
        else:
            db.init_schema(schema)

    print("Starting environment processes and gateway...")
    procs = server_manager.start_all()
    print("Ports:", {name: info["port"] for name, info in procs.items()})

    try:
        executor = PlanExecutor(procs["gateway"]["url"])
        judge = DeterministicLocalJudge()

        tasks = generate_all()
        print(f"Generated {len(tasks)} tasks ({sum(1 for t in tasks if t.has_mistake)} with an injected mistake).")

        tools_called = set()
        judge_pass = 0
        oracle_pass = 0
        mistake_total = 0
        mistake_oracle_caught = 0
        mistake_judge_caught = 0
        clean_oracle_pass = 0
        clean_count = 0
        rows = []

        start = time.time()
        for i, task in enumerate(tasks):
            transcript = executor.execute(task.id, task.instruction, task.executed_plan)
            for s in transcript.steps:
                tools_called.add(s.tool)

            jv = judge.verdict(transcript)
            ov = oracle_interpreter.grade(task)

            if jv.passed:
                judge_pass += 1
            if ov.passed:
                oracle_pass += 1

            if task.has_mistake:
                mistake_total += 1
                if not ov.passed:
                    mistake_oracle_caught += 1
                if not jv.passed:
                    mistake_judge_caught += 1
            else:
                clean_count += 1
                if ov.passed:
                    clean_oracle_pass += 1

            rows.append(
                {
                    "task_id": task.id,
                    "template": task.template,
                    "has_mistake": task.has_mistake,
                    "mistake_note": task.mistake_note,
                    "judge_passed": jv.passed,
                    "oracle_passed": ov.passed,
                    "oracle_mismatches": ov.mismatches,
                }
            )

            if (i + 1) % 60 == 0:
                print(f"  ... {i + 1}/{len(tasks)} tasks run")

        elapsed = time.time() - start

        total = len(tasks)
        judge_pass_rate = 100.0 * judge_pass / total
        oracle_pass_rate = 100.0 * oracle_pass / total
        gap = judge_pass_rate - oracle_pass_rate

        lines = []
        lines.append("agent-task-environment-state-benchmark: 420-task benchmark run")
        lines.append(f"total tasks: {total}")
        lines.append(f"tasks with injected mistake: {mistake_total}")
        lines.append(f"clean tasks: {clean_count}")
        lines.append(f"distinct tools exercised: {len(tools_called)}/13 -> {sorted(tools_called)}")
        lines.append("")
        lines.append(f"deterministic local judge: {judge_pass}/{total} passed ({judge_pass_rate:.2f}%)")
        lines.append(f"expected-state oracle:     {oracle_pass}/{total} passed ({oracle_pass_rate:.2f}%)")
        lines.append(f"overcredit gap (judge - oracle): {gap:.2f} percentage points")
        lines.append("")
        lines.append(f"of {mistake_total} mistake-injected tasks: oracle caught {mistake_oracle_caught}, local judge caught {mistake_judge_caught}")
        lines.append(f"of {clean_count} clean tasks: oracle passed {clean_oracle_pass} ({100.0 * clean_oracle_pass / clean_count:.2f}%)")
        lines.append(f"elapsed: {elapsed:.1f}s for {total} tasks through the real gateway and real Postgres")
        lines.append("")
        lines.append("per-task detail (first 20 shown here; full detail in docs/benchmark_output.json):")
        for row in rows[:20]:
            lines.append(f"  {row['task_id']} [{row['template']}] mistake={row['has_mistake']} judge_pass={row['judge_passed']} oracle_pass={row['oracle_passed']}")
            if row["oracle_mismatches"]:
                for m in row["oracle_mismatches"]:
                    lines.append(f"      mismatch: {m}")

        out_text = "\n".join(lines)
        print(out_text)

        docs_dir = Path(__file__).resolve().parents[1] / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "benchmark_output.txt").write_text(out_text + "\n", encoding="utf-8")
        (docs_dir / "benchmark_output.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    finally:
        print("Stopping environment processes and gateway...")
        server_manager.stop_all(procs)


if __name__ == "__main__":
    main()
