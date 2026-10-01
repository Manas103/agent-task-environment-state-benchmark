"""The real claude -p live sample: runs the first 20 generated tasks (a mix of
mistake-injected and clean tasks across all six templates) through the real
gateway, then asks a real `claude -p` subprocess to judge each transcript, and
compares its verdict against both the oracle and the deterministic local judge.
Writes raw output to docs/claude_judge_sample.txt.

This script resets the environment schemas itself so it can be run
independently of scripts/run_benchmark.py without a primary-key collision on
the first 20 task ids.

Usage: python scripts/run_claude_judge_sample.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import server_manager
from src import db
from src.executor.executor import PlanExecutor
from src.judge.claude_cli_judge import ClaudeCliJudgeClient
from src.judge.deterministic_judge import DeterministicLocalJudge
from src.oracle import oracle_interpreter
from src.tasks.task_generator import generate_all

SAMPLE_SIZE = 20


def main():
    for schema in ("crm", "ticketing", "inventory"):
        db.reset_schema(schema)

    procs = server_manager.start_all()
    try:
        executor = PlanExecutor(procs["gateway"]["url"])
        det_judge = DeterministicLocalJudge()
        claude_judge = ClaudeCliJudgeClient()

        tasks = generate_all()[:SAMPLE_SIZE]
        lines = [f"agent-task-environment-state-benchmark: real claude -p live sample ({SAMPLE_SIZE} tasks)"]

        claude_pass = 0
        claude_parseable = 0
        agree_with_oracle = 0
        agree_with_det_judge = 0

        start = time.time()
        for i, task in enumerate(tasks):
            transcript = executor.execute(task.id, task.instruction, task.executed_plan)
            ov = oracle_interpreter.grade(task)
            dv = det_judge.verdict(transcript)
            cv = claude_judge.verdict(transcript)

            parseable = not cv.reason.startswith("unparseable") and not cv.reason.startswith("claude CLI call failed")
            if parseable:
                claude_parseable += 1
            if cv.passed:
                claude_pass += 1
            if cv.passed == ov.passed:
                agree_with_oracle += 1
            if cv.passed == dv.passed:
                agree_with_det_judge += 1

            lines.append(
                f"[{i+1}/{SAMPLE_SIZE}] {task.id} mistake={task.has_mistake} "
                f"({task.mistake_note or 'n/a'}) -> oracle_pass={ov.passed} det_judge_pass={dv.passed} "
                f"claude_pass={cv.passed} parseable={parseable}"
            )
            lines.append(f"    claude raw: {cv.reason[:300]!r}")

        elapsed = time.time() - start

        lines.append("")
        lines.append(f"claude -p calls made: {SAMPLE_SIZE}")
        lines.append(f"parseable verdicts: {claude_parseable}/{SAMPLE_SIZE}")
        lines.append(f"claude judge passed: {claude_pass}/{SAMPLE_SIZE}")
        lines.append(f"claude agreed with oracle: {agree_with_oracle}/{SAMPLE_SIZE}")
        lines.append(f"claude agreed with deterministic local judge: {agree_with_det_judge}/{SAMPLE_SIZE}")
        lines.append(f"elapsed: {elapsed:.1f}s for {SAMPLE_SIZE} real claude -p subprocess calls")

        out_text = "\n".join(lines)
        print(out_text)

        docs_dir = Path(__file__).resolve().parents[1] / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "claude_judge_sample.txt").write_text(out_text + "\n", encoding="utf-8")
    finally:
        server_manager.stop_all(procs)


if __name__ == "__main__":
    main()
