"""Composition-root lifecycle regression coverage."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN = PROJECT_ROOT / "main.py"


def test_controller_shutdown_is_owned_by_main_finally_block() -> None:
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    main_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    lifecycle = next(
        node
        for node in ast.walk(main_function)
        if isinstance(node, ast.Try)
        and any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "shutdown"
            for final_node in node.finalbody
            for child in ast.walk(final_node)
        )
    )

    assert lifecycle.finalbody
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "exec"
        for body_node in lifecycle.body
        for node in ast.walk(body_node)
    )
