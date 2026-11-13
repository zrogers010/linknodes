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


def test_git_checkout_creates_from_current_head_not_origin():
    """Verify checkout creates branch from current HEAD, not origin/data/refresh.
    
    This prevents the day-2 failure where checking out from origin/data/refresh
    conflicts with uncommitted changes in the working tree.
    """
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should use: git checkout -B data/refresh (creates from current HEAD)
    assert 'git checkout -B "$BRANCH_NAME"' in workflow_content, (
        "Workflow must use 'git checkout -B $BRANCH_NAME' to create from current HEAD"
    )
    
    # Should NOT reference origin/ in the checkout command
    assert 'origin/$BRANCH_NAME' not in workflow_content or \
           'git fetch origin "$BRANCH_NAME"' in workflow_content, (
        "Workflow must not checkout from origin/$BRANCH_NAME "
        "(only fetch is OK, but not checkout -B ... origin/...)"
    )
    
    # Specifically check that we don't do the broken pattern
    assert 'git checkout -B "$BRANCH_NAME" "origin/$BRANCH_NAME"' not in workflow_content, (
        "CRITICAL: Must not checkout from origin/$BRANCH_NAME - causes day-2 failure"
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
    - Other: Error (not 0 or 10)
    
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


def test_workflow_handles_crash_as_error():
    """Verify workflow treats non-0/10 exit codes as errors, not no-changes."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should check for exit code 0 (changes)
    assert "[ $rc -eq 0 ]" in workflow_content, (
        "Workflow must check for exit code 0 (changes)"
    )
    
    # Should check for exit code 10 (no changes)
    assert "[ $rc -eq 10 ]" in workflow_content or "elif [ $rc -eq 10 ]" in workflow_content, (
        "Workflow must check for exit code 10 (no changes)"
    )
    
    # Should fail on other exit codes (crash/error)
    assert "exit $rc" in workflow_content, (
        "Workflow must exit with error code when check_data_changes.py crashes"
    )
    
    # Verify the error case doesn't set has_changes=false
    # (it should fail the job, not treat it as no-changes)
    lines = workflow_content.split('\n')
    in_check_section = False
    has_proper_error_handling = False
    
    for i, line in enumerate(lines):
        if 'check_data_changes.py' in line:
            in_check_section = True
        if in_check_section and 'exit $rc' in line:
            # Check that before this line, we don't set has_changes=false for all non-zero
            prev_lines = '\n'.join(lines[max(0, i-10):i])
            # Should have elif for 10, then else that exits
            if '[ $rc -eq 10 ]' in prev_lines or 'elif [ $rc -eq 10 ]' in prev_lines:
                has_proper_error_handling = True
            break
    
    assert has_proper_error_handling, (
        "Workflow must distinguish between exit 10 (no-changes) and crashes (error)"
    )


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


def test_ci_workflow_has_workflow_dispatch():
    """Verify CI workflow can be dispatched (not workflow_call).
    
    workflow_dispatch allows gh workflow run ci.yml --ref data/refresh,
    which creates runs on the refresh branch that attach to PR commits.
    """
    ci_workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    ci_content = ci_workflow_path.read_text()
    
    # Should have workflow_dispatch trigger
    assert "workflow_dispatch:" in ci_content, (
        "CI workflow must have workflow_dispatch trigger for gh workflow run"
    )
    
    # Should NOT use workflow_call (that inherits caller's SHA, runs on main)
    assert "workflow_call:" not in ci_content, (
        "CI workflow must NOT use workflow_call - it tests main, not the refresh branch"
    )


def test_refresh_workflow_dispatches_ci_with_ref():
    """Verify refresh workflow dispatches CI on the refresh branch."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should dispatch CI workflow with --ref
    assert "gh workflow run ci.yml --ref" in workflow_content, (
        "Refresh workflow must dispatch CI with --ref to run on refresh branch"
    )
    
    # Should specify the data/refresh branch
    assert '--ref "$BRANCH_NAME"' in workflow_content or \
           '--ref "data/refresh"' in workflow_content, (
        "Dispatch must specify --ref with the refresh branch name"
    )
    
    # Should NOT use workflow_call (that tests main, not refresh branch)
    assert "uses: ./.github/workflows/ci.yml" not in workflow_content, (
        "Must NOT use workflow_call - it inherits caller's SHA and tests main"
    )


def test_refresh_workflow_has_actions_write_permission():
    """Verify refresh workflow has actions: write for gh workflow run."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "refresh-data.yml"
    workflow_content = workflow_path.read_text()
    
    # Should have actions: write permission
    assert "actions: write" in workflow_content, (
        "Refresh workflow needs 'actions: write' permission for gh workflow run"
    )
