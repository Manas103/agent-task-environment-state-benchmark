"""Orchestrates the memory extension's measurement: builds the fact pool
(60 target users, 1,000 distractor users), scores the four qualities
separately against the real oracle, measures the transcript-judge's
overcredit gap on the same task set, and reports read latency, throughput
and cost per session from the same OpenTelemetry spans this repository's
gateway already uses (`src/telemetry.py`), not a separate instrumentation
path.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from src import telemetry
from src.memory import oracle, store
from src.memory.judge import judge_pass
from src.memory.retrieval import best_answer, score_and_rank
from src.memory.tasks import N_DISTRACTOR_USERS, N_TARGET_USERS, build_corpus

ISOLATION_PROBE_SAMPLE = 60  # how many recall/isolation tasks also get the unscoped non-vacuousness check


def run_scoped_task(cur, task) -> tuple[list[dict], str | None]:
    with telemetry.tool_call_span("memory_read", "memory", {"user_id": task.user_id, "query": task.query_text}) as record:
        facts = store.facts_for_user(cur, task.user_id)
        top_k = score_and_rank(facts, task.query_text)
        answer = best_answer(top_k)
        record["response"] = {"top_k": top_k, "answer": answer["value"] if answer else None}
        record["ok"] = answer is not None
    return top_k, (answer["value"] if answer else None)


def run_unscoped_probe(cur, task) -> bool:
    """True if, with the per-user scope removed, a distractor user's fact
    would have outranked or tied the correct answer at the top of the
    ranking, for proving the zero-leak result below is not vacuous."""
    all_facts = store.all_facts_unscoped(cur)
    top_k = score_and_rank(all_facts, task.query_text)
    return bool(top_k) and top_k[0].get("user_id") != task.user_id


def main(docs_dir: Path) -> dict:
    docs_dir.mkdir(parents=True, exist_ok=True)
    telemetry.configure(docs_dir / "memory_otel_spans.jsonl")

    conn = store.get_memory_conn()
    conn.autocommit = True
    try:
        store.reset_schema(conn)
        with conn.cursor() as cur:
            tasks = build_corpus(cur, seed=2026)

        per_quality = {k: {"oracle_pass": 0, "judge_pass": 0, "total": 0} for k in ("recall", "freshness", "isolation", "abstention")}
        start = time.perf_counter()
        with conn.cursor() as cur:
            for task in tasks:
                top_k, answer = run_scoped_task(cur, task)
                oracle_ok = oracle.grade(task, top_k)
                judge_ok = judge_pass(top_k, answer)
                per_quality[task.kind]["total"] += 1
                per_quality[task.kind]["oracle_pass"] += int(oracle_ok)
                per_quality[task.kind]["judge_pass"] += int(judge_ok)
        elapsed_s = time.perf_counter() - start

        isolation_tasks = [t for t in tasks if t.kind == "isolation"][:ISOLATION_PROBE_SAMPLE]
        with conn.cursor() as cur:
            would_leak = sum(1 for t in isolation_tasks if run_unscoped_probe(cur, t))
    finally:
        conn.close()

    total_oracle_pass = sum(v["oracle_pass"] for v in per_quality.values())
    total_judge_pass = sum(v["judge_pass"] for v in per_quality.values())
    total_tasks = sum(v["total"] for v in per_quality.values())

    spans = [json.loads(line) for line in (docs_dir / "memory_otel_spans.jsonl").read_text().splitlines() if line.strip()]
    latencies = [s["attributes"]["agentbench.latency_ms"] for s in spans]
    costs = [s["attributes"]["agentbench.cost_usd"] for s in spans]

    report = {
        "n_target_users": N_TARGET_USERS,
        "n_distractor_users": N_DISTRACTOR_USERS,
        "total_tasks": total_tasks,
        "per_quality": {
            k: {
                "total": v["total"],
                "oracle_pass": v["oracle_pass"],
                "oracle_pass_pct": round(100 * v["oracle_pass"] / v["total"], 2),
                "judge_pass": v["judge_pass"],
                "judge_pass_pct": round(100 * v["judge_pass"] / v["total"], 2),
            }
            for k, v in per_quality.items()
        },
        "overall": {
            "oracle_pass_pct": round(100 * total_oracle_pass / total_tasks, 2),
            "judge_pass_pct": round(100 * total_judge_pass / total_tasks, 2),
            "overcredit_gap_points": round(100 * total_judge_pass / total_tasks - 100 * total_oracle_pass / total_tasks, 2),
        },
        "isolation_non_vacuousness": {
            "probed": len(isolation_tasks),
            "would_leak_without_scope": would_leak,
            "would_leak_pct": round(100 * would_leak / len(isolation_tasks), 2) if isolation_tasks else None,
        },
        "spans": {
            "n_spans": len(spans),
            "elapsed_s": round(elapsed_s, 4),
            "throughput_reads_per_sec": round(total_tasks / elapsed_s, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 4),
            "avg_cost_usd_per_session": round(sum(costs) / len(costs), 8),
            "total_cost_usd": round(sum(costs), 8),
        },
    }
    (docs_dir / "memory_measure_report.json").write_text(json.dumps(report, indent=2))

    lines = [
        f"tasks: {total_tasks} ({N_TARGET_USERS} target users x 4 qualities), {N_DISTRACTOR_USERS} distractor users",
        "",
        "per-quality oracle vs judge pass rate:",
    ]
    for k, v in report["per_quality"].items():
        lines.append(f"  {k:<11} oracle {v['oracle_pass']}/{v['total']} ({v['oracle_pass_pct']}%)  judge {v['judge_pass']}/{v['total']} ({v['judge_pass_pct']}%)")
    lines += [
        "",
        f"overall oracle pass: {report['overall']['oracle_pass_pct']}%",
        f"overall judge pass:  {report['overall']['judge_pass_pct']}%",
        f"overcredit gap: {report['overall']['overcredit_gap_points']} points",
        "",
        f"isolation non-vacuousness: without the per-user scope, {would_leak}/{len(isolation_tasks)} probed queries "
        f"would have surfaced a distractor's fact first ({report['isolation_non_vacuousness']['would_leak_pct']}%)",
        "",
        f"spans: {report['spans']['n_spans']} reads in {report['spans']['elapsed_s']}s "
        f"({report['spans']['throughput_reads_per_sec']} reads/sec)",
        f"avg read latency: {report['spans']['avg_latency_ms']} ms",
        f"avg cost/session: ${report['spans']['avg_cost_usd_per_session']}",
    ]
    (docs_dir / "memory_benchmark_output.txt").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    import sys

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs")
    result = main(out_dir)
    print(json.dumps(result, indent=2))
