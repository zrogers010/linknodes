#!/usr/bin/env python3
"""
Mutation testing for refresh checks
====================================
Tests that each of the 6 checks makes the build exit non-zero on bad input.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path

backend = Path(__file__).parent


def apply_mutation(file_path, old_text, new_text):
    """Apply a mutation to a file."""
    content = file_path.read_text()
    if old_text not in content:
        raise ValueError(f"Could not find text to mutate in {file_path}")
    mutated = content.replace(old_text, new_text, 1)
    file_path.write_text(mutated)


def revert_mutation(file_path, backup_path):
    """Revert a mutation."""
    shutil.copy2(backup_path, file_path)


def run_build(script_name):
    """Run a build script and return exit code."""
    result = subprocess.run(
        ["python3", script_name],
        cwd=backend,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def test_mutation(name, file_path, old_text, new_text, build_script, test_script=None):
    """Test a single mutation."""
    print(f"\n{'='*80}")
    print(f"Mutation: {name}")
    print(f"File: {file_path.name}")
    print(f"{'='*80}")
    
    # Backup original file
    backup = tempfile.NamedTemporaryFile(delete=False, mode='w')
    backup_path = Path(backup.name)
    shutil.copy2(file_path, backup_path)
    
    try:
        # Apply mutation
        print(f"Applying mutation...")
        apply_mutation(file_path, old_text, new_text)
        
        # Run build script
        print(f"Running {build_script}...")
        exit_code, stdout, stderr = run_build(build_script)
        
        if exit_code == 0:
            print(f"❌ FAIL: Build succeeded (exit {exit_code}) but should have failed")
            print("Last 20 lines of output:")
            print('\n'.join((stdout + stderr).split('\n')[-20:]))
            return False
        else:
            print(f"✓ Build failed as expected (exit {exit_code})")
            # Show the error message
            error_output = (stdout + stderr)
            if "REFRESH CHECK FAILED" in error_output:
                for line in error_output.split('\n'):
                    if "REFRESH CHECK FAILED" in line or "%" in line or "below" in line:
                        print(f"  {line}")
            else:
                print("  Error output:")
                print('\n'.join(error_output.split('\n')[-10:]))
        
        # Revert mutation
        revert_mutation(file_path, backup_path)
        
        # Run test script if provided
        if test_script:
            print(f"Running test {test_script}...")
            test_result = subprocess.run(
                ["python3", "-m", "pytest", test_script, "-v", "-k", name.replace(" ", "_").replace("-", "_")],
                cwd=backend,
                capture_output=True,
                text=True
            )
            if test_result.returncode != 0:
                print(f"❌ Test failed after revert")
                return False
            else:
                print(f"✓ Test passes after revert")
        
        return True
        
    finally:
        # Clean up
        revert_mutation(file_path, backup_path)
        backup_path.unlink()


def main():
    print("="*80)
    print("MUTATION TESTING: Refresh Checks")
    print("="*80)
    print("Testing that each check causes build to exit non-zero on bad input")
    
    mutations = [
        {
            "name": "RDD non-200 response",
            "file": backend / "build_registry.py",
            "old": "http_responses[f\"{RDD_BASE}/{rdd_file}.json\"] = resp.status_code",
            "new": "http_responses[f\"{RDD_BASE}/{rdd_file}.json\"] = 404  # MUTANT",
            "build": "build_registry.py",
            "test": "test_refresh_checks.py::test_check_rdd_response_codes_fails_on_404"
        },
        {
            "name": "Mapping rate below threshold",
            "file": backend / "build_operators.py",
            "old": "check_transmitter_mapping_rate(network_key, s[\"mapped\"], effective_total, threshold=98.0)",
            "new": "pass  # MUTANT: check disabled",
            "build": "build_operators.py",
            "test": "test_refresh_checks.py::test_check_transmitter_mapping_rate_fails_below_threshold"
        },
        {
            "name": "RPC failure rate exceeds threshold",
            "file": backend / "build_operators.py",
            "old": "check_rpc_failure_rate(total_rpc_failures, total_rpc_calls, max_failure_pct=30.0)",
            "new": "pass  # MUTANT: check disabled",
            "build": "build_operators.py",
            "test": "test_refresh_checks.py::test_check_rpc_failure_rate_fails_above_30_percent"
        },
        {
            "name": "Feed count change exceeds 20%",
            "file": backend / "refresh_checks.py",
            "old": "if change_pct > max_change_pct:",
            "new": "if False:  # MUTANT: check disabled",
            "build": None,  # This is tested via pytest only
            "test": "test_refresh_checks.py::test_check_feed_count_change_fails_above_20_percent"
        },
        {
            "name": "Hidden operators leak as public",
            "file": backend / "data/operator_overrides.json",
            "old": '    "cl-ocr-nav-",',
            "new": '',  # Remove the pattern
            "build": "build_operators.py",
            "test": "test_refresh_checks.py::test_check_hidden_operators_fails_on_id_match"
        },
        {
            "name": "CCIP API non-200 response",
            "file": backend / "build_ccip_registry.py",
            "old": "http_responses[MAINNET_API_URL] = mainnet_status",
            "new": "http_responses[MAINNET_API_URL] = 500  # MUTANT",
            "build": "build_ccip_registry.py",
            "test": "test_refresh_checks.py::test_check_rdd_response_codes_fails_on_404"
        }
    ]
    
    results = []
    for m in mutations:
        success = test_mutation(
            m["name"],
            m["file"],
            m["old"],
            m["new"],
            m["build"],
            m.get("test")
        )
        results.append({
            "name": m["name"],
            "file": m["file"].name,
            "build": m["build"],
            "test": m.get("test", "N/A"),
            "killed": "✓" if success else "❌"
        })
    
    # Print summary table
    print("\n" + "="*80)
    print("MUTATION TESTING SUMMARY")
    print("="*80)
    print(f"{'Mutant':<40} {'Build Script':<25} {'Killed':<10}")
    print("-"*80)
    for r in results:
        print(f"{r['name']:<40} {r['build'] or 'N/A':<25} {r['killed']:<10}")
    print("="*80)
    
    total = len(results)
    killed = sum(1 for r in results if r["killed"] == "✓")
    print(f"\nResults: {killed}/{total} mutants killed")
    
    return 0 if killed == total else 1


if __name__ == "__main__":
    exit(main())
