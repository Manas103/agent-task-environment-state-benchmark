import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.finance import permission
from src.finance.tools import FAMILIES


def test_five_roles_one_per_family():
    assert len(permission.ROLES) == 5
    assert {r.granted_family for r in permission.ROLES} == set(FAMILIES)


def test_own_family_tool_is_allowed():
    role = permission.ROLES[0]
    own_tool = permission.TOOL_NAME_BY_FAMILY[role.granted_family]
    result = permission.check([own_tool], role)
    assert result.allowed is True


def test_out_of_scope_tool_is_refused_and_named():
    role = permission.ROLES[0]
    other_family = [f for f in FAMILIES if f != role.granted_family][0]
    other_tool = permission.TOOL_NAME_BY_FAMILY[other_family]
    result = permission.check([other_tool], role)
    assert result.allowed is False
    assert result.offending_tool == other_tool
    assert result.offending_family == other_family


def test_adversarial_suite_is_120_plans_all_refused():
    suite = permission.build_adversarial_suite()
    assert len(suite) == 120
    for case in suite:
        result = permission.check(case["tool_calls"], case["role"])
        assert result.allowed is False
        assert result.offending_tool == case["expected_offending_tool"]
