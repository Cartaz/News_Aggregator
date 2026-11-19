"""Structural rules that protect real invariants, checked on imports, not on wording."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _top_level(modules: set[str]) -> set[str]:
    return {module.split(".", 1)[0] for module in modules}


@pytest.mark.parametrize("package", ["core", "config"])
def test_domain_layers_do_not_depend_on_qt_or_ui(package: str) -> None:
    offenders = {
        str(path.relative_to(PROJECT_ROOT)): sorted(
            _top_level(_imported_modules(path)) & {"PySide6", "shiboken6", "ui"}
        )
        for path in (PROJECT_ROOT / package).glob("*.py")
    }
    assert {name: found for name, found in offenders.items() if found} == {}


def test_config_does_not_depend_on_core() -> None:
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in (PROJECT_ROOT / "config").glob("*.py")
        if "core" in _top_level(_imported_modules(path))
    ]
    assert offenders == []


def test_every_qml_text_element_renders_plain_text() -> None:
    """Feed content is untrusted: no QML text element may interpret markup."""
    element = re.compile(r"\b(Text|TextEdit)\s*\{")
    offenders: list[str] = []
    for path in (PROJECT_ROOT / "ui" / "qml").glob("*.qml"):
        source = path.read_text(encoding="utf-8")
        for match in element.finditer(source):
            # Text elements here are flat, so the body ends at the first brace.
            body = source[match.end():].split("}", 1)[0]
            if not re.search(r"textFormat:\s*(Text|TextEdit)\.PlainText", body):
                line = source.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.name}:{line}")
    assert offenders == []
