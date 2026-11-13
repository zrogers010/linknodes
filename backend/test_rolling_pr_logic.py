"""
Test rolling PR logic (branch management and PR update/create decision).

These tests verify the logic used in refresh-data.yml for managing
a single rolling PR branch instead of creating daily branches.
"""

import subprocess
from pathlib import Path


def test_rolling_pr_branch_name_is_stable():
    """Verify the rolling PR uses a fixed branch name."""
    # The workflow should use a fixed branch name, not a dated one
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should have BRANCH_NAME="data/refresh" (fixed)
    assert 'BRANCH_NAME="data/refresh"' in workflow_content, (
        "Workflow should use fixed branch 'data/refresh', not daily dated branches"
    )
    
    # Should NOT have data/refresh-${{ (dated branches)
    assert "data/refresh-${{" not in workflow_content, (
        "Workflow should not create dated branches like data/refresh-YYYY-MM-DD"
    )


def test_refresh_workflow_has_pr_update_logic():
    """Verify the workflow checks for existing PRs and updates them."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should check if PR exists
    assert "gh pr list --head" in workflow_content, (
        "Workflow should check for existing PR from the rolling branch"
    )
    
    # Should have both create and edit logic
    assert "gh pr create" in workflow_content, (
        "Workflow should create new PR if none exists"
    )
    assert "gh pr edit" in workflow_content, (
        "Workflow should update existing PR instead of creating duplicate"
    )


def test_refresh_workflow_force_pushes_to_rolling_branch():
    """Verify the workflow force-pushes to update the rolling branch."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should force push to rolling branch (git push -f)
    assert "git push -f" in workflow_content or "git push --force" in workflow_content, (
        "Workflow should force-push to rolling branch to update it daily"
    )


def test_check_data_changes_exit_codes_preserved():
    """
    Verify check_data_changes.py still returns distinct exit codes.
    
    Exit codes:
    - 0: Changes detected
    - 10: No changes detected
    - Other: Error
    
    This ensures the workflow can distinguish between "no changes" and "failure".
    """
    script_path = Path(__file__).parent / "check_data_changes.py"
    script_content = script_path.read_text()
    
    # Should define distinct exit codes
    assert "EXIT_CHANGES = 0" in script_content
    assert "EXIT_NO_CHANGES = 10" in script_content
    assert "EXIT_ERROR = 1" in script_content
    
    # Should return these codes
    assert "return EXIT_CHANGES" in script_content
    assert "return EXIT_NO_CHANGES" in script_content
    assert "return EXIT_ERROR" in script_content


def test_refresh_workflow_handles_no_changes_cleanly():
    """Verify the workflow handles no-changes case without creating PR."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should check for has_changes before creating PR
    assert "if: steps.check_changes.outputs.has_changes == 'true'" in workflow_content or \
           "if: needs.refresh.outputs.has_changes == 'true'" in workflow_content, (
        "Workflow should only create/update PR when changes are detected"
    )
    
    # Should handle exit code 10 (no changes)
    assert "[ $rc -eq 10 ]" in workflow_content, (
        "Workflow should recognize exit code 10 as 'no changes' (not an error)"
    )


def test_ci_workflow_is_reusable():
    """Verify CI workflow can be called from other workflows."""
    ci_workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    ci_content = ci_workflow_path.read_text()
    
    # Should have workflow_call trigger
    assert "workflow_call:" in ci_content, (
        "CI workflow should be reusable via workflow_call"
    )


def test_refresh_workflow_calls_ci():
    """Verify refresh workflow calls CI after pushing changes."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should call CI workflow
    assert "uses: ./.github/workflows/ci.yml" in workflow_content, (
        "Refresh workflow should call CI workflow to run checks on refresh branch"
    )
