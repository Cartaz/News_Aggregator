"""Release workflow safety contracts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_waits_for_successful_main_ci() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_run:" in workflow
    assert 'workflows: ["CI"]' in workflow
    assert "types: [completed]" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow


def test_release_targets_the_ci_verified_commit() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "RELEASE_SHA: ${{ github.event.workflow_run.head_sha }}" in workflow
    assert '--target "$RELEASE_SHA"' in workflow
    assert '--target "$GITHUB_SHA"' not in workflow
