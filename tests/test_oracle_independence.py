"""Mechanical check for the 'expected-state oracle sharing no code with the
executor' claim: walks the real import graph of src.oracle.* and asserts none
of it imports src.executor, src.gateway, or src.environments."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FORBIDDEN_PREFIXES = ("src.executor", "src.gateway", "src.environments")


def _imported_modules(py_file: Path):
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_oracle_package_imports_nothing_from_executor_gateway_or_environments():
    oracle_dir = ROOT / "src" / "oracle"
    checked = 0
    for py_file in oracle_dir.glob("*.py"):
        checked += 1
        for mod in _imported_modules(py_file):
            for forbidden in FORBIDDEN_PREFIXES:
                assert not mod.startswith(forbidden), (
                    f"{py_file.name} imports {mod!r}, which starts with forbidden prefix {forbidden!r}; "
                    "the oracle must share no code with the executor side"
                )
    assert checked >= 3, "expected to check reference_simulator.py, actual_state_reader.py, oracle_interpreter.py"
