import shutil

import pytest

from silicon.oracles import run_lint, simulate_updown_counter, simulate_updown_counter_transitions
from silicon.tasks import GOLDEN_COMPARATOR, RTL_DIR


def test_lint_catches_missing_default():
    bad = "module m; always_comb begin case (x) 2'b00: y=1; endcase end endmodule"
    assert "missing_default_case" in run_lint(bad)
    good = "module m; always_comb begin case (x) 2'b00: y=1; default: y=0; endcase end endmodule"
    assert "missing_default_case" not in run_lint(good)


def test_counter_wraps_up_and_down():
    seq = [(True, True)] * 16  # 16 up-steps from 0 should return to 0
    trace = simulate_updown_counter(seq)
    assert trace[-1] == 0
    assert max(trace) == 15


def test_wraparound_bug_saturates_instead_of_wrapping():
    seq = [(True, True)] * 16
    golden = simulate_updown_counter(seq, wraparound_bug=False)
    mutant = simulate_updown_counter(seq, wraparound_bug=True)
    assert golden[-1] == 0
    assert mutant[-1] == 15
    assert golden != mutant


@pytest.mark.skipif(not shutil.which("wsl.exe"), reason="wsl.exe not available on this machine")
def test_yosys_equivalence_real_golden_vs_golden():
    from silicon.oracles import yosys_equivalence

    assert yosys_equivalence(GOLDEN_COMPARATOR, "comparator4") is True


@pytest.mark.skipif(not shutil.which("wsl.exe"), reason="wsl.exe not available on this machine")
def test_yosys_equivalence_catches_a_real_mutation():
    from silicon.oracles import yosys_equivalence

    mutated = GOLDEN_COMPARATOR.replace("assign gt_o = a_i > b_i;", "assign gt_o = a_i < b_i;")
    assert yosys_equivalence(mutated, "comparator4") is False
