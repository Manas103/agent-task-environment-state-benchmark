import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.oracle import reference_simulator
from src.permission import roles as role_defs, scope_checker
from src.permission.adversarial_generator import build_adversarial_suite
from src.tasks.task_generator import generate_all


def test_tool_catalog_has_exactly_13_tools():
    assert len(config.TOOL_CATALOG) == 13


def test_generate_all_produces_420_tasks_with_injected_mistakes():
    tasks = generate_all()
    assert len(tasks) == 420
    mistakes = sum(1 for t in tasks if t.has_mistake)
    assert mistakes == 140  # every third task, global_idx % 3 == 0


def test_reference_simulator_adjust_and_transfer_stock():
    from src.executor.plan import Plan, ToolCall

    plan = Plan(steps=(
        ToolCall("create_product", {"id": "P1", "name": "Widget", "category": "HARDWARE"}),
        ToolCall("adjust_stock", {"product_id": "P1", "warehouse": "WH-EAST", "delta": 10}),
        ToolCall("transfer_stock", {"product_id": "P1", "from_warehouse": "WH-EAST", "to_warehouse": "WH-WEST", "quantity": 4}),
    ))
    state = reference_simulator.simulate(plan)
    assert state["stock"][("P1", "WH-EAST")] == 6
    assert state["stock"][("P1", "WH-WEST")] == 4
    assert state["products"]["P1"]["active"] is True


def test_adversarial_suite_is_120_plans_all_refused():
    suite = build_adversarial_suite()
    assert len(suite) == 120
    refused = 0
    for entry in suite:
        result = scope_checker.check(entry["plan"], entry["role"])
        if not result.allowed:
            refused += 1
            assert result.offending_tool == entry["expected_offending_tool"]
    assert refused == 120


def test_admin_role_is_never_in_the_adversarial_suite():
    suite = build_adversarial_suite()
    assert all(entry["role"] != role_defs.ADMIN for entry in suite)
