"""CLI entry point for the finance-workflow extension's 420-task benchmark
plus the 120-plan adversarial scope-refusal suite. Writes
docs/finance_measure_report.json and docs/finance_benchmark_output.txt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.finance.measure import main  # noqa: E402

if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs"
    print(json.dumps(main(out_dir), indent=2))
