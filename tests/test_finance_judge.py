import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.finance.judge import judge_pass


def test_judge_passes_whenever_tool_reports_ok_true():
    assert judge_pass({"ok": True, "status": "flagged"}) is True


def test_judge_fails_only_when_tool_reports_ok_false():
    assert judge_pass({"ok": False}) is False
    assert judge_pass({}) is False
