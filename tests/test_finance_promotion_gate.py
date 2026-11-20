import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_finance_promotion_gate import evaluate


def test_no_baseline_yet_always_promotes():
    promote, regressed = evaluate({"invoice_three_way_match": 66.67}, None)
    assert promote is True
    assert regressed == []


def test_equal_or_improved_accuracy_promotes():
    current = {"a": 66.67, "b": 70.0}
    baseline = {"a": 66.67, "b": 66.67}
    promote, regressed = evaluate(current, baseline)
    assert promote is True
    assert regressed == []


def test_one_regressed_family_blocks_and_is_named():
    current = {"a": 66.67, "b": 46.67}
    baseline = {"a": 66.67, "b": 66.67}
    promote, regressed = evaluate(current, baseline)
    assert promote is False
    assert regressed == ["b"]


def test_a_family_missing_from_baseline_is_not_treated_as_regressed():
    current = {"a": 66.67, "new_family": 10.0}
    baseline = {"a": 66.67}
    promote, regressed = evaluate(current, baseline)
    assert promote is True
    assert regressed == []
