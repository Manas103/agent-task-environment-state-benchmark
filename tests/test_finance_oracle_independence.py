"""Mechanical check for the finance extension's 'oracle shares no code with
the executor' claim, the same AST-walk convention as
tests/test_oracle_independence.py applied to src/finance/oracle.py and
src/finance/tools.py.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FORBIDDEN_PREFIXES = ("src.finance.tools",)


def _imported_modules(py_file: Path):
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_finance_oracle_imports_nothing_from_finance_tools():
    oracle_file = ROOT / "src" / "finance" / "oracle.py"
    for mod in _imported_modules(oracle_file):
        for forbidden in FORBIDDEN_PREFIXES:
            assert not mod.startswith(forbidden), (
                f"oracle.py imports {mod!r}, which starts with forbidden prefix {forbidden!r}; "
                "the finance oracle must share no code with the executor"
            )
