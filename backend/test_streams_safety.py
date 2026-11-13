"""
Test safety checks for streams_247.json to prevent accidental data loss.
"""
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from build_registry import main as build_main, MAINNET_CHAINS


def test_safety_check_prevents_empty_streams(tmp_path):
    """Test that the safety check prevents writing an empty streams_247.json."""
    
    # Create a mock git show that returns a committed version with 17 streams
    mock_committed = {
        "version": "1.0.0",
        "count": 17,
        "streams": [{"name": f"stream-{i}"} for i in range(17)]
    }
    
    def mock_run(*args, **kwargs):
        result = MagicMock()
        if "git" in args[0] and "show" in args[0]:
            result.returncode = 0
            result.stdout = json.dumps(mock_committed)
        else:
            result.returncode = 1
        return result
    
    # Mock build_registry to return 0 streams (simulating the bug)
    with patch('subprocess.run', side_effect=mock_run):
        with patch('build_registry.build_registry') as mock_build:
            # Simulate the bug: return empty streams
            mock_build.return_value = ({}, 0, tmp_path / "build_tmp", [])
            
            # Should raise ValueError due to safety check
            with tempfile.TemporaryDirectory() as tmpdir:
                with pytest.raises(ValueError, match="streams_247.json would be emptied"):
                    build_main(output_dir=Path(tmpdir))


def test_safety_check_prevents_large_reduction(tmp_path):
    """Test that the safety check prevents >50% reduction in streams count."""
    
    mock_committed = {
        "version": "1.0.0",
        "count": 20,
        "streams": [{"name": f"stream-{i}"} for i in range(20)]
    }
    
    def mock_run(*args, **kwargs):
        result = MagicMock()
        if "git" in args[0] and "show" in args[0]:
            result.returncode = 0
            result.stdout = json.dumps(mock_committed)
        else:
            result.returncode = 1
        return result
    
    with patch('subprocess.run', side_effect=mock_run):
        with patch('build_registry.build_registry') as mock_build:
            # Return only 5 streams (75% reduction)
            mock_streams = [{"name": f"stream-{i}"} for i in range(5)]
            mock_build.return_value = ({}, 0, tmp_path / "build_tmp", mock_streams)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                with pytest.raises(ValueError, match="would drop by.*75"):
                    build_main(output_dir=Path(tmpdir))


def test_safety_check_allows_small_changes(tmp_path):
    """Test that small changes (within 50%) are allowed."""
    
    mock_committed = {
        "version": "1.0.0",
        "count": 20,
        "streams": [{"name": f"stream-{i}"} for i in range(20)]
    }
    
    def mock_run(*args, **kwargs):
        result = MagicMock()
        if "git" in args[0] and "show" in args[0]:
            result.returncode = 0
            result.stdout = json.dumps(mock_committed)
        else:
            result.returncode = 1
        return result
    
    with patch('subprocess.run', side_effect=mock_run):
        with patch('build_registry.build_registry') as mock_build:
            # Return 15 streams (25% reduction - should be OK)
            mock_streams = [{"name": f"stream-{i}"} for i in range(15)]
            mainnet_temp = tmp_path / "mainnet_tmp"
            testnet_temp = tmp_path / "testnet_tmp"
            
            # Return tuple with 4 values for both calls
            mock_build.side_effect = [
                ({"networks": {}}, 100, mainnet_temp, mock_streams),
                ({"networks": {}}, 50, testnet_temp, [])
            ]
            
            with patch('build_registry.write_nodes'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Should not raise
                    build_main(output_dir=Path(tmpdir))
                    
                    # Verify streams_247.json was written
                    streams_path = Path(tmpdir) / "streams_247.json"
                    assert streams_path.exists()
                    data = json.loads(streams_path.read_text())
                    assert data["count"] == 15


def test_safety_check_allows_increase(tmp_path):
    """Test that increases in stream count are allowed."""
    
    mock_committed = {
        "version": "1.0.0",
        "count": 17,
        "streams": [{"name": f"stream-{i}"} for i in range(17)]
    }
    
    def mock_run(*args, **kwargs):
        result = MagicMock()
        if "git" in args[0] and "show" in args[0]:
            result.returncode = 0
            result.stdout = json.dumps(mock_committed)
        else:
            result.returncode = 1
        return result
    
    with patch('subprocess.run', side_effect=mock_run):
        with patch('build_registry.build_registry') as mock_build:
            # Return 18 streams (increase)
            mock_streams = [{"name": f"stream-{i}"} for i in range(18)]
            mainnet_temp = tmp_path / "mainnet_tmp"
            testnet_temp = tmp_path / "testnet_tmp"
            
            mock_build.side_effect = [
                ({"networks": {}}, 100, mainnet_temp, mock_streams),
                ({"networks": {}}, 50, testnet_temp, [])
            ]
            
            with patch('build_registry.write_nodes'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Should not raise
                    build_main(output_dir=Path(tmpdir))
                    
                    # Verify streams_247.json was written with new count
                    streams_path = Path(tmpdir) / "streams_247.json"
                    assert streams_path.exists()
                    data = json.loads(streams_path.read_text())
                    assert data["count"] == 18


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
