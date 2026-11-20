"""The CI promotion gate: compares this run's per-family oracle pass rate
(docs/finance_measure_report.json, produced by scripts/run_finance_benchmark.py)
against the committed baseline (config/finance_baseline.json) and refuses to
promote if any family's accuracy regressed. On a clean or improved run it
writes the new baseline and exits 0; on a regression it exits 1 and names
every regressed family, which is what .github/workflows/finance-promotion-gate.yml
runs in CI.

--simulate-regression lowers one family's measured accuracy in a copy of the
real report before comparing, so the blocking path is exercised against a
real, reproducible scenario rather than only a hand-written unit test; it
never writes to the real report or the real baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.finance import baseline as baseline_mod  # noqa: E402

REGRESSION_PENALTY_PCT = 20.0
EPSILON = 1e-9


def evaluate(current: dict, baseline: dict | None) -> tuple[bool, list[str]]:
    """Returns (promote, regressed_families)."""
    if baseline is None:
        return True, []
    regressed = [
        family
        for family, pct in current.items()
        if family in baseline and pct < baseline[family] - EPSILON
    ]
    return (len(regressed) == 0), regressed


def _report_to_per_family_pct(report: dict) -> dict:
    return {family: v["oracle_pass_pct"] for family, v in report["benchmark"]["per_family"].items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--baseline-path", default=None)
    parser.add_argument("--simulate-regression", default=None, help="family name to artificially regress, for a reproducible demonstration run")
    args = parser.parse_args()

    report = json.loads((Path(args.docs_dir) / "finance_measure_report.json").read_text())
    current = _report_to_per_family_pct(report)

    if args.simulate_regression:
        family = args.simulate_regression
        current = dict(current)
        current[family] = max(0.0, current[family] - REGRESSION_PENALTY_PCT)

    baseline_path = Path(args.baseline_path) if args.baseline_path else baseline_mod.DEFAULT_BASELINE_PATH
    baseline = baseline_mod.load_baseline(baseline_path)

    promote, regressed = evaluate(current, baseline)

    if promote:
        if not args.simulate_regression:
            baseline_mod.save_baseline(current, baseline_path)
        print(f"PROMOTE: current per-family accuracy {current}")
        print(f"baseline: {baseline if baseline is not None else '(none yet; this run becomes the baseline)'}")
        return 0

    print(f"BLOCKED: regressed families: {regressed}")
    for family in regressed:
        print(f"  {family}: baseline {baseline[family]}% -> current {current[family]}%")
    return 1


if __name__ == "__main__":
    sys.exit(main())
