"""Reads and writes the per-family accuracy baseline the CI promotion gate
(scripts/run_finance_promotion_gate.py) compares a new measurement run
against. Stored as plain JSON under config/, not docs/ (docs/ holds raw run
output, which is expected to change every run; the baseline is meant to
persist across runs and only move forward on an explicit promotion).
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parents[2] / "config" / "finance_baseline.json"


def load_baseline(path: Path = DEFAULT_BASELINE_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_baseline(per_family_pass_pct: dict, path: Path = DEFAULT_BASELINE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(per_family_pass_pct, indent=2, sort_keys=True) + "\n")
