"""Regression tests for the repository installation contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_script_matches_documented_flow() -> None:
    script = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert script.startswith("#!/usr/bin/env bash\n")
    assert "python3" in script
    assert '"${PYTHON_BIN}" -m venv "${VENV_DIR}"' in script
    assert 'pip install -r "${REQUIREMENTS_FILE}"' in script
    assert ".venv/bin/python main.py" in script
    assert ".local/share/applications" not in script
    assert "update-desktop-database" not in script


def test_runtime_and_development_requirements_are_separated() -> None:
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    development = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "PySide6" in runtime
    assert "pytest" not in runtime.lower()
    assert "-r requirements.txt" in development
    assert "pytest" in development.lower()


def test_local_environment_artifacts_are_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in (".venv/", "__pycache__/", ".pytest_cache/", "*.log"):
        assert entry in ignore
