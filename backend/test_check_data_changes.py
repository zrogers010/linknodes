"""
Tests for check_data_changes.py exit codes
"""

import subprocess
import tempfile
import json
import shutil
from pathlib import Path


def test_check_data_changes_exits_10_on_no_changes():
    """
    Test that check_data_changes.py exits with code 10 when there are no changes.
    
    Kills mutants:
    - EXIT_NO_CHANGES changed to 0 or 1
    - no-changes path returns wrong exit code
    """
    # Run check_data_changes.py with no actual changes (right after build)
    backend = Path(__file__).parent
    result = subprocess.run(
        ["python3", "check_data_changes.py"],
        cwd=backend,
        capture_output=True,
        text=True
    )
    
    # Should exit with code 10 for no changes
    assert result.returncode == 10, \
        f"Expected exit code 10 for no changes, got {result.returncode}"
    
    assert "has_changes=false" in result.stdout, \
        f"Expected 'has_changes=false' in output, got: {result.stdout}"


def test_check_data_changes_exits_0_on_changes():
    """
    Test that check_data_changes.py exits with code 0 when there are changes.
    
    Kills mutants:
    - EXIT_CHANGES changed to 1 or 10
    - changes path returns wrong exit code
    """
    backend = Path(__file__).parent
    
    # Create a temporary registry file with a change
    registry_path = backend / "registry.json"
    
    # Check if tree is dirty (don't mutate if user has uncommitted changes)
    git_status = subprocess.run(
        ["git", "status", "--porcelain", str(registry_path.relative_to(backend.parent))],
        cwd=backend.parent,
        capture_output=True,
        text=True
    )
    
    if git_status.stdout.strip():
        # Tree is dirty, use a temp copy approach
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy backend directory structure
            tmp_backend = Path(tmpdir) / "backend"
            tmp_backend.mkdir()
            
            # Copy only the files needed for the test
            for fname in ["check_data_changes.py", "registry.json"]:
                shutil.copy(backend / fname, tmp_backend / fname)
            
            # Initialize git repo in tmpdir
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)
            
            # Modify the file
            tmp_registry = tmp_backend / "registry.json"
            registry = json.loads(tmp_registry.read_text())
            registry["_test_change"] = "temporary"
            tmp_registry.write_text(json.dumps(registry, indent=1))
            
            # Run check in tmpdir
            result = subprocess.run(
                ["python3", "check_data_changes.py"],
                cwd=tmp_backend,
                capture_output=True,
                text=True
            )
    else:
        # Tree is clean, safe to mutate temporarily
        original_content = registry_path.read_text()
        
        try:
            # Add a temporary field to force a change
            registry = json.loads(original_content)
            registry["_test_change"] = "temporary"
            registry_path.write_text(json.dumps(registry, indent=1))
            
            # Run check
            result = subprocess.run(
                ["python3", "check_data_changes.py"],
                cwd=backend,
                capture_output=True,
                text=True
            )
        finally:
            # Restore original
            registry_path.write_text(original_content)
    
    # Should exit with code 0 for changes detected
    assert result.returncode == 0, \
        f"Expected exit code 0 for changes, got {result.returncode}"
    
    assert "has_changes=true" in result.stdout, \
        f"Expected 'has_changes=true' in output, got: {result.stdout}"


def test_check_data_changes_exits_error_on_invalid_json():
    """
    Test that check_data_changes.py exits with code 1 (error) on parse failures.
    
    Kills mutants:
    - error path returns EXIT_NO_CHANGES (10)
    - error path returns EXIT_CHANGES (0)
    - exceptions not caught properly
    """
    backend = Path(__file__).parent
    
    # Use registry_testnet.json as test target
    temp_file = backend / "registry_testnet.json"
    original_content = None
    
    if temp_file.exists():
        original_content = temp_file.read_text()
    
    try:
        # Write invalid JSON
        temp_file.write_text("{invalid json")
        
        # Run check
        result = subprocess.run(
            ["python3", "check_data_changes.py"],
            cwd=backend,
            capture_output=True,
            text=True
        )
        
        # Should exit with code 1 (error), not 0 (changes) or 10 (no changes)
        assert result.returncode == 1, \
            f"Expected exit code 1 for error, got {result.returncode}"
        
        assert result.returncode not in (0, 10), \
            f"Error should not return EXIT_CHANGES (0) or EXIT_NO_CHANGES (10), got {result.returncode}"
    
    finally:
        # Restore or remove
        if original_content is not None:
            temp_file.write_text(original_content)
        elif temp_file.exists():
            temp_file.unlink()
