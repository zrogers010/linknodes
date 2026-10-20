#!/usr/bin/env python3
"""
Check for meaningful data changes (ignoring timestamps).

Returns exit code 0 if there are changes, 1 if no changes.
"""

import json
import sys
from pathlib import Path


def strip_timestamps(data):
    """Recursively remove generated_at and crawled_at fields."""
    if isinstance(data, dict):
        return {
            k: strip_timestamps(v)
            for k, v in data.items()
            if k not in ("generated_at", "crawled_at")
        }
    elif isinstance(data, list):
        return [strip_timestamps(item) for item in data]
    else:
        return data


def main():
    backend = Path(__file__).parent
    
    files_to_check = [
        backend / "registry.json",
        backend / "registry_testnet.json",
        backend / "data" / "operators.json",
        backend / "data" / "feed_operators.json",
        backend / "ccip_registry.json",
        backend / "ccip_registry_testnet.json",
    ]
    
    # Add all nodes files
    nodes_dir = backend / "data" / "nodes"
    if nodes_dir.exists():
        files_to_check.extend(nodes_dir.glob("*.json"))
    
    has_changes = False
    
    for file_path in files_to_check:
        if not file_path.exists():
            continue
        
        # Read current version
        try:
            current = json.loads(file_path.read_text())
            current_stripped = strip_timestamps(current)
        except Exception as e:
            # Treat parse errors as failures, not "no changes"
            print(f"ERROR: Failed to parse {file_path.name}: {e}")
            raise
        
        # Get committed version
        import subprocess
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:{file_path.relative_to(backend.parent)}"],
                capture_output=True,
                text=True,
                cwd=backend.parent
            )
            if result.returncode == 0:
                committed = json.loads(result.stdout)
                committed_stripped = strip_timestamps(committed)
                
                if json.dumps(current_stripped, sort_keys=True) != json.dumps(committed_stripped, sort_keys=True):
                    print(f"Changes detected in {file_path.name}")
                    has_changes = True
            else:
                # New file
                print(f"New file: {file_path.name}")
                has_changes = True
        except Exception as e:
            print(f"Error checking {file_path.name}: {e}")
            has_changes = True
    
    if has_changes:
        print("has_changes=true")
        return 0  # Changes found
    else:
        print("has_changes=false")
        return 1  # No changes


if __name__ == "__main__":
    sys.exit(main())
