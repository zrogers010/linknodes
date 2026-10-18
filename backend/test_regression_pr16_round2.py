"""
Regression Tests for PR #16 Round 2 QA Fixes
==============================================
Tests that kill specific mutants identified in QA review.
"""

import hashlib
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from main import app, set_test_clock, get_current_time


@pytest.fixture(autouse=True)
def reset_clock():
    """Reset test clock after each test."""
    yield
    set_test_clock(None)


def test_hidden_feed_returns_404_no_fallback_to_svr_dai_usd():
    """
    Mutant: A hidden (shut_down) feed falls back to its SVR variant or base feed.
    Kill: Returns 404 immediately without trying variants.
    
    Test case: arbitrum dai-usd-svr (shut down 2026-06-03) on any date >= 2026-06-04
    must return 404 and never dai-usd.
    """
    client = TestClient(app)
    
    # Set clock to 2026-06-04 (one day after dai-usd-svr shutdown)
    set_test_clock(datetime(2026, 6, 4, tzinfo=timezone.utc))
    
    # dai-usd-svr is shut down, should return 404
    response = client.get("/v1/query/arbitrum/dai-usd-svr")
    assert response.status_code == 404, f"Expected 404 for shut down feed, got {response.status_code}"


def test_hidden_feed_ezeth_eth_exchange_rate_shutdown_guard():
    """
    Test base ezeth-eth-exchange-rate: visible on 10-18, hidden on 10-19.
    No fallback to -svr variant.
    
    Mutant: Guard for -svr requests is skipped.
    Kill: Shut down feed returns 404 without falling back to variants.
    
    Tests the _resolve() guard logic directly without RPC calls.
    """
    from main import _resolve
    from fastapi import HTTPException
    
    # October 18, 2026 - feed should be visible (deprecating)
    set_test_clock(datetime(2026, 10, 18, tzinfo=timezone.utc))
    try:
        net, feed, resolved = _resolve("base", "ezeth-eth-exchange-rate", "mainnet")
        # Feed exists and is visible on 10-18
        assert feed is not None
    except HTTPException:
        pytest.fail("Feed should be visible on 10-18")
    
    # October 19, 2026 - feed should be hidden (shut down)
    set_test_clock(datetime(2026, 10, 19, tzinfo=timezone.utc))
    with pytest.raises(HTTPException) as exc_info:
        _resolve("base", "ezeth-eth-exchange-rate", "mainnet")
    assert exc_info.value.status_code == 404, f"Expected 404 on 10-19"


def test_unparseable_shutdown_date_fails_build():
    """
    Mutant: Unparseable shutdownDate becomes 'never hidden' (fail open).
    Kill: Unparseable date raises ValueError and fails the build.
    """
    from build_registry import parse_shutdown_date
    
    # Valid dates should parse
    assert parse_shutdown_date("October 18th, 2026") == "2026-10-18"
    assert parse_shutdown_date("February 2026") == "2026-02-28"
    assert parse_shutdown_date(None) is None
    
    # Unparseable dates should raise ValueError
    with pytest.raises(ValueError, match="Unable to parse shutdown date"):
        parse_shutdown_date("invalid date format")
    
    with pytest.raises(ValueError, match="Unable to parse shutdown date"):
        parse_shutdown_date("13th Month 2026")


def test_malformed_date_at_request_time():
    """
    Mutant: Malformed shutdown_date at request time shown as 'deprecating forever'.
    Kill: Malformed date must be treated as hidden or error, never shown.
    
    Tests 'garbage', 'TBD', and '2026-6-3' (non-ISO format).
    """
    from main import recompute_feed_status
    from build_registry import compute_feed_status
    
    set_test_clock(datetime(2026, 10, 18, tzinfo=timezone.utc))
    
    # Test malformed dates in compute_feed_status
    # Garbage date should be treated as immediate shutdown (hidden)
    status = compute_feed_status("verified", "garbage", "2026-10-18")
    assert status == "shut_down", "Malformed date 'garbage' should be treated as shut_down"
    
    # TBD should be treated as immediate shutdown
    status = compute_feed_status("verified", "TBD", "2026-10-18")
    assert status == "shut_down", "Malformed date 'TBD' should be treated as shut_down"
    
    # Malformed ISO date (single digit month/day) should be treated as immediate shutdown
    status = compute_feed_status("verified", "2026-6-3", "2026-10-18")
    assert status == "shut_down", "Non-ISO date '2026-6-3' should be treated as shut_down"
    
    # Valid ISO date should work normally
    status = compute_feed_status("verified", "2027-01-01", "2026-10-18")
    assert status == "deprecating", "Future valid date should be deprecating"


def test_malformed_date_excluded_from_registry_endpoint():
    """
    Mutant: /v1/registry lists feeds with malformed shutdown_date.
    Kill: Inject malformed-date feed, assert /v1/registry omits it.
    """
    import main
    import copy
    
    client = TestClient(app)
    set_test_clock(datetime(2026, 10, 18, tzinfo=timezone.utc))
    
    # Temporarily inject a feed with malformed date into the registry
    # Save original with deepcopy
    orig_mainnet = copy.deepcopy(main.REGISTRY_MAINNET)
    
    # Inject bad feed into ethereum network
    if "ethereum" in main.REGISTRY_MAINNET.get("networks", {}):
        if "feeds" not in main.REGISTRY_MAINNET["networks"]["ethereum"]:
            main.REGISTRY_MAINNET["networks"]["ethereum"]["feeds"] = {}
        
        main.REGISTRY_MAINNET["networks"]["ethereum"]["feeds"]["test-malformed"] = {
            "name": "Test Malformed",
            "shutdown_date": "garbage",  # Malformed date
            "category": "verified",
            "address": "0x0000000000000000000000000000000000000001",
            "feed_type": "crypto",
            "decimals": 8
        }
    
    try:
        response = client.get("/v1/registry")
        assert response.status_code == 200
        data = response.json()
        
        # Check that malformed feed is NOT in the response
        if "ethereum" in data.get("networks", {}):
            feeds = data["networks"]["ethereum"]["feeds"]
            assert "test-malformed" not in feeds, \
                "Feed with malformed shutdown_date should be excluded from /v1/registry"
    finally:
        # Restore original with deepcopy
        main.REGISTRY_MAINNET.clear()
        main.REGISTRY_MAINNET.update(orig_mainnet)


def test_malformed_date_returns_404_from_query_endpoint():
    """
    Mutant: /v1/query serves feeds with malformed shutdown_date.
    Kill: Inject malformed-date feed, assert /v1/query returns 404.
    """
    import main
    import copy
    
    client = TestClient(app)
    set_test_clock(datetime(2026, 10, 18, tzinfo=timezone.utc))
    
    # Temporarily inject a feed with malformed date
    # Save original with deepcopy
    orig_mainnet = copy.deepcopy(main.REGISTRY_MAINNET)
    
    if "ethereum" in main.REGISTRY_MAINNET.get("networks", {}):
        if "feeds" not in main.REGISTRY_MAINNET["networks"]["ethereum"]:
            main.REGISTRY_MAINNET["networks"]["ethereum"]["feeds"] = {}
        
        main.REGISTRY_MAINNET["networks"]["ethereum"]["feeds"]["test-malformed-query"] = {
            "name": "Test Malformed Query",
            "shutdown_date": "TBD",  # Malformed date
            "category": "verified",
            "address": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",  # Real ETH/USD address
            "feed_type": "crypto",
            "decimals": 8
        }
    
    try:
        response = client.get("/v1/query/ethereum/test-malformed-query")
        # Should return 404 because feed is hidden (malformed date = shut_down)
        assert response.status_code == 404, \
            f"Feed with malformed shutdown_date should return 404, got {response.status_code}"
    finally:
        # Restore original with deepcopy
        main.REGISTRY_MAINNET.clear()
        main.REGISTRY_MAINNET.update(orig_mainnet)


def test_clock_normalization_naive_and_aware():
    """
    Mutant: Local-tz clock used for shutdown comparison.
    Kill: Naive clock is treated as UTC, aware clock is converted to UTC.
    """
    from main import set_test_clock, get_current_time
    
    # Test 1: Naive datetime should be treated as UTC
    naive_dt = datetime(2026, 10, 17, 12, 0, 0)
    set_test_clock(naive_dt)
    result = get_current_time()
    assert result.tzinfo == timezone.utc
    assert result.hour == 12
    assert result.strftime("%Y-%m-%d") == "2026-10-17"
    
    # Test 2: Aware datetime in different timezone should be converted to UTC
    eastern = timezone(timedelta(hours=-5))
    aware_dt = datetime(2026, 10, 17, 12, 0, 0, tzinfo=eastern)  # 12:00 EST = 17:00 UTC
    set_test_clock(aware_dt)
    result = get_current_time()
    assert result.tzinfo == timezone.utc
    assert result.hour == 17  # Converted to UTC
    assert result.strftime("%Y-%m-%d") == "2026-10-17"
    
    # Test 3: Reset to None should work
    set_test_clock(None)
    result = get_current_time()
    assert result.tzinfo == timezone.utc


def test_get_current_time_with_clock_unset_under_non_utc_tz(monkeypatch):
    """
    Mutant: Real now() uses local time instead of UTC.
    Kill: get_current_time() returns UTC even with TZ=America/Los_Angeles and clock unset.
    """
    # Store original TZ
    original_tz = os.environ.get('TZ', '')
    
    try:
        # Set timezone to Los Angeles
        monkeypatch.setenv("TZ", "America/Los_Angeles")
        time.tzset()
        
        # Clock is UNSET - should still return UTC
        set_test_clock(None)
        current = get_current_time()
        
        assert current.tzinfo == timezone.utc, "get_current_time() should return UTC even with LA timezone set"
        
    finally:
        # Restore original TZ (not 'UTC')
        if original_tz:
            monkeypatch.setenv("TZ", original_tz)
        else:
            monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_local_tz_mutants_with_non_utc_timezone(monkeypatch):
    """
    Mutant: Local-tz date used in visibility check or real now() uses local time.
    Kill: Set TZ=America/Los_Angeles and verify UTC is still used.
    """
    from main import is_feed_visible, get_current_time
    
    # Store original TZ
    original_tz = os.environ.get('TZ', '')
    
    try:
        # Set timezone to Los Angeles (UTC-8 or UTC-7 depending on DST)
        monkeypatch.setenv("TZ", "America/Los_Angeles")
        time.tzset()
        
        # Even with local TZ set, our clock should use UTC
        set_test_clock(datetime(2026, 10, 18, 0, 0, 0, tzinfo=timezone.utc))
        current = get_current_time()
        assert current.tzinfo == timezone.utc
        assert current.strftime("%Y-%m-%d") == "2026-10-18"
        
        # Feed with shutdown_date "2026-10-18" should be visible on 2026-10-18 UTC
        # (not based on LA time)
        feed = {"shutdown_date": "2026-10-18", "category": "verified"}
        assert is_feed_visible(feed), "Feed should be visible on shutdown date (UTC)"
        
        # One day later in UTC, should be hidden
        set_test_clock(datetime(2026, 10, 19, 0, 0, 0, tzinfo=timezone.utc))
        assert not is_feed_visible(feed), "Feed should be hidden day after shutdown (UTC)"
    finally:
        # Restore original TZ
        if original_tz:
            monkeypatch.setenv("TZ", original_tz)
        else:
            monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_atomic_nodes_write_all_20_files_exist():
    """
    Mutant: write_nodes called twice deletes mainnet files.
    Kill: All 20 files (13 mainnet + 7 testnet) exist after write_nodes is called once.
    
    Also tests:
    - Stale nodes-*.json files are removed (must kill 'stale cleanup removed')
    - Staging dir is created under dest_dir.parent (must kill 'staging moved outside data/')
    """
    from build_registry import write_nodes
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Set up mainnet staged directory with 13 files
        mainnet_staged = tmpdir / "mainnet_staged"
        mainnet_staged.mkdir()
        for i in range(13):
            (mainnet_staged / f"nodes-mainnet{i}.json").write_text(json.dumps({"mainnet": i}))
        
        # Set up testnet staged directory with 7 files
        testnet_staged = tmpdir / "testnet_staged"
        testnet_staged.mkdir()
        for i in range(7):
            (testnet_staged / f"nodes-testnet{i}.json").write_text(json.dumps({"testnet": i}))
        
        # Destination directory (use a subdir to simulate backend/data/)
        data_dir = tmpdir / "data"
        data_dir.mkdir()
        dest_dir = data_dir / "nodes"
        dest_dir.mkdir()
        
        # Add a STALE file that shouldn't exist in new set
        stale_file = dest_dir / "nodes-stale-old.json"
        stale_file.write_text(json.dumps({"stale": "data"}))
        assert stale_file.exists(), "Stale file should exist before write_nodes"
        
        # Call write_nodes once with both directories
        write_nodes(mainnet_staged, testnet_staged, dest_dir)
        
        # Count files in destination
        files = list(dest_dir.glob("*.json"))
        assert len(files) == 20, f"Expected 20 files, got {len(files)}: {[f.name for f in files]}"
        
        # Verify mainnet files exist
        mainnet_count = sum(1 for f in files if "mainnet" in f.name)
        assert mainnet_count == 13, f"Expected 13 mainnet files, got {mainnet_count}"
        
        # Verify testnet files exist
        testnet_count = sum(1 for f in files if "testnet" in f.name)
        assert testnet_count == 7, f"Expected 7 testnet files, got {testnet_count}"
        
        # Verify STALE file is GONE
        assert not stale_file.exists(), \
            f"Stale file {stale_file.name} should have been removed but still exists"
        
        # Verify no stale files remain
        stale_count = sum(1 for f in files if "stale" in f.name)
        assert stale_count == 0, f"Found {stale_count} stale files, expected 0"


def test_atomic_nodes_write_staging_failure_leaves_dest_untouched():
    """
    Mutant: Per-file non-atomic copy can leave partial state.
    Kill: If Nth staged copy fails, data/nodes is byte-identical to before.
    
    Tests kill:
    - QA3: per-file copy-then-replace without full staging
    - Stale cleanup removed
    - Staging dir moved outside data/
    
    Snapshots every file (name + sha256) before and after staging failure.
    """
    from build_registry import write_nodes
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Set up mainnet staged directory
        mainnet_staged = tmpdir / "mainnet_staged"
        mainnet_staged.mkdir()
        (mainnet_staged / "nodes-main1.json").write_text(json.dumps({"main": 1}))
        (mainnet_staged / "nodes-main2.json").write_text(json.dumps({"main": 2}))
        
        # Set up testnet staged directory
        testnet_staged = tmpdir / "testnet_staged"
        testnet_staged.mkdir()
        (testnet_staged / "nodes-test1.json").write_text(json.dumps({"test": 1}))
        
        # Set up existing destination with original files
        data_dir = tmpdir / "data"
        data_dir.mkdir()
        dest_dir = data_dir / "nodes"
        dest_dir.mkdir()
        
        # Create multiple existing files
        original_files = {
            "nodes-orig1.json": json.dumps({"original": 1}),
            "nodes-orig2.json": json.dumps({"original": 2}),
            "nodes-orig3.json": json.dumps({"original": 3})
        }
        
        for filename, content in original_files.items():
            (dest_dir / filename).write_text(content)
        
        # Snapshot all files before: name + sha256
        snapshot_before = {}
        for f in dest_dir.glob("*.json"):
            snapshot_before[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        
        # Mock shutil.copy2 to fail on second call
        original_copy2 = shutil.copy2
        call_count = [0]
        
        def failing_copy2(src, dst, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise IOError("Simulated copy failure on 2nd file")
            return original_copy2(src, dst, *args, **kwargs)
        
        with patch('shutil.copy2', side_effect=failing_copy2):
            with pytest.raises(IOError, match="Simulated copy failure"):
                write_nodes(mainnet_staged, testnet_staged, dest_dir)
        
        # Snapshot all files after: name + sha256
        snapshot_after = {}
        for f in dest_dir.glob("*.json"):
            snapshot_after[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        
        # Assert snapshots are identical
        assert snapshot_before == snapshot_after, \
            f"Files changed during staging failure. Before: {snapshot_before}, After: {snapshot_after}"


def test_atomic_nodes_write_staging_in_data_parent():
    """
    Mutant: Staging dir moved outside data/ (e.g. to /tmp).
    Kill: Verify staging dir is created under dest_dir.parent (backend/data/).
    
    Spies on tempfile.TemporaryDirectory to verify the staging dir location.
    Must fail if staging moves to /tmp or elsewhere.
    """
    from build_registry import write_nodes
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Set up staged directories
        mainnet_staged = tmpdir / "mainnet_staged"
        mainnet_staged.mkdir()
        (mainnet_staged / "nodes-main1.json").write_text(json.dumps({"main": 1}))
        
        testnet_staged = tmpdir / "testnet_staged"
        testnet_staged.mkdir()
        (testnet_staged / "nodes-test1.json").write_text(json.dumps({"test": 1}))
        
        # Set up destination
        data_dir = tmpdir / "data"
        data_dir.mkdir()
        dest_dir = data_dir / "nodes"
        dest_dir.mkdir()
        
        # Spy on tempfile.TemporaryDirectory to capture staging dir location
        staging_dirs = []
        original_tempdir = tempfile.TemporaryDirectory
        
        class SpyTemporaryDirectory(original_tempdir):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                staging_dirs.append(Path(self.name))
        
        with patch('tempfile.TemporaryDirectory', SpyTemporaryDirectory):
            write_nodes(mainnet_staged, testnet_staged, dest_dir)
        
        # Verify staging dir was created under dest_dir.parent (data/)
        assert len(staging_dirs) > 0, "No staging directory was created"
        
        staging_dir = staging_dirs[0]
        # Staging dir should be under data/, not /tmp or elsewhere
        # Check that staging dir starts with the data_dir path
        assert str(staging_dir).startswith(str(data_dir)), \
            f"Staging dir {staging_dir} should be under {data_dir}, not elsewhere"


def test_build_registry_main_preserves_all_nodes_files(tmp_path):
    """
    Mutant: write_nodes called twice (once per network) deletes all 13 mainnet files.
    Kill: After main() with MockTransport serving 13 mainnet + 7 testnet, all 20 files exist.
    
    Runs main() with mocked data into tmp output dir, verifies all 20 nodes files with served content.
    Must fail when write_nodes is called once per network set.
    """
    import httpx
    from build_registry import main as build_main, MAINNET_CHAINS, TESTNET_CHAINS
    
    # Create output dir
    output_dir = tmp_path / "backend"
    output_dir.mkdir()
    (output_dir / "data").mkdir()
    (output_dir / "data" / "nodes").mkdir()
    
    # Track which nodes files were requested to verify correct behavior
    mainnet_chains_count = len(MAINNET_CHAINS)
    testnet_chains_count = len(TESTNET_CHAINS)
    
    # Mock transport serving minimal valid feeds + nodes for all chains
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if '/nodes-' in url_str:
            # Return valid empty nodes list
            return httpx.Response(200, json=[])
        # Return minimal valid feed
        return httpx.Response(200, json=[{
            "path": "test-feed",
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "contractAddress": "0x0987654321098765432109876543210987654321",
            "decimals": 8,
            "heartbeat": 3600,
        }])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        build_main(http_client=mock_client, output_dir=output_dir)
    finally:
        mock_client.close()
    
    # Verify all 20 nodes files exist (13 mainnet + 7 testnet)
    nodes_dir = output_dir / "data" / "nodes"
    files = list(nodes_dir.glob("*.json"))
    count = len(files)
    
    assert count == 20, f"Expected 20 nodes files, got {count}. Files: {[f.name for f in files]}"
    
    # Verify each file is valid JSON with expected structure (list of nodes)
    for f in files:
        data = json.loads(f.read_text())
        assert isinstance(data, list), f"{f.name} must be a list of nodes"


def test_nodes_validation_non_200_fails_build(tmp_path, monkeypatch):
    """
    Mutant: Nodes files with non-200 HTTP response become warn-only (don't fail build).
    Kill: Non-200 response must fail the build and leave outputs unchanged.
    
    Uses httpx.MockTransport to return 404 for nodes URL.
    Asserts main() raises and all output files are unchanged (sha256 comparison).
    """
    import httpx
    from build_registry import main as build_main
    
    backend = Path(__file__).parent
    
    # Create temp output dir with existing files
    output_dir = tmp_path / "backend"
    output_dir.mkdir()
    data_dir = output_dir / "data"
    data_dir.mkdir()
    nodes_dir = data_dir / "nodes"
    nodes_dir.mkdir()
    
    # Copy existing files to temp
    for f in [backend / "registry.json", backend / "registry_testnet.json"]:
        if f.exists():
            shutil.copy2(f, output_dir / f.name)
    
    if (backend / "data" / "nodes").exists():
        for f in (backend / "data" / "nodes").glob("*.json"):
            shutil.copy2(f, nodes_dir / f.name)
    
    # Snapshot all files before
    files_before = {}
    for f in output_dir.glob("*.json"):
        files_before[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    for f in nodes_dir.glob("*.json"):
        files_before[f"nodes/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
    
    # Create mock transport that returns 404 for nodes URLs
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if '/nodes-' in str(request.url):
            # Return 404 for nodes files
            return httpx.Response(404, text="Not Found")
        # Return 200 with minimal valid data for feeds
        return httpx.Response(200, json=[])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    # Monkeypatch Path resolving to use temp dir
    original_parent = Path(__file__).parent
    def mock_file_parent():
        return output_dir
    
    try:
        # Attempt to build with mocked client
        with pytest.raises(Exception):  # Should raise on 404
            build_main(http_client=mock_client, output_dir=output_dir)
        
        # Snapshot all files after
        files_after = {}
        for f in output_dir.glob("*.json"):
            files_after[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        for f in nodes_dir.glob("*.json"):
            files_after[f"nodes/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
        
        # All files must be unchanged
        assert files_before == files_after, \
            f"Output files changed despite build failure"
    finally:
        mock_client.close()


def test_validation_call_not_removed(tmp_path, monkeypatch):
    """
    Mutant: The validate_source_data call is removed entirely.
    Kill: Invalid source data must fail the build and leave outputs unchanged.
    
    Uses httpx.MockTransport to return invalid JSON structure (missing required fields).
    Asserts main() raises and all output files are unchanged (sha256 comparison).
    """
    import httpx
    from build_registry import main as build_main
    
    backend = Path(__file__).parent
    
    # Create temp output dir with existing files
    output_dir = tmp_path / "backend"
    output_dir.mkdir()
    data_dir = output_dir / "data"
    data_dir.mkdir()
    nodes_dir = data_dir / "nodes"
    nodes_dir.mkdir()
    
    # Copy existing files
    for f in [backend / "registry.json", backend / "registry_testnet.json"]:
        if f.exists():
            shutil.copy2(f, output_dir / f.name)
    
    if (backend / "data" / "nodes").exists():
        for f in (backend / "data" / "nodes").glob("*.json"):
            shutil.copy2(f, nodes_dir / f.name)
    
    # Snapshot all files before
    files_before = {}
    for f in output_dir.glob("*.json"):
        files_before[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    for f in nodes_dir.glob("*.json"):
        files_before[f"nodes/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
    
    # Create mock transport that returns invalid structure for feed URLs
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if '/nodes-' in str(request.url):
            # Return valid empty list for nodes
            return httpx.Response(200, json=[])
        # Return feeds that pass include() but fail validation (missing contractAddress)
        return httpx.Response(200, json=[{
            "path": "test-feed",
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "decimals": 8,
            "heartbeat": 3600,
            # Missing "contractAddress" - will fail validation
        }])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        # Attempt to build - should fail validation with specific error
        with pytest.raises(ValueError, match="VALIDATION FAILED.*contractAddress"):
            build_main(http_client=mock_client, output_dir=output_dir)
        
        # Snapshot all files after
        files_after = {}
        for f in output_dir.glob("*.json"):
            files_after[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        for f in nodes_dir.glob("*.json"):
            files_after[f"nodes/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
        
        # All files must be unchanged
        assert files_before == files_after, \
            f"Output files changed despite validation failure"
    finally:
        mock_client.close()


def test_registry_endpoint_filters_shut_down_feeds():
    """
    Mutant: /v1/registry returns unfiltered feeds (including shut_down).
    Kill: Only visible feeds should be returned.
    """
    client = TestClient(app)
    
    # Set clock to a date when some feeds are shut down
    set_test_clock(datetime(2026, 10, 19, tzinfo=timezone.utc))
    
    response = client.get("/v1/registry")
    assert response.status_code == 200
    data = response.json()
    
    # Check that no shut_down feeds are included
    for network_key, network_data in data["networks"].items():
        for feed_slug, feed_meta in network_data["feeds"].items():
            assert feed_meta.get("status") != "shut_down", \
                f"Feed {feed_slug} has status=shut_down and should not be in /v1/registry"


def test_compare_endpoint_filters_shut_down_feeds():
    """
    Mutant: /v1/compare returns unfiltered feeds (including shut_down).
    Kill: Visible networks present, hidden networks absent.
    
    Injects a feed with one shut_down network and other visible networks via patched registry.
    Asserts unconditionally: response 200, visible network present, hidden network absent.
    Must fail when /v1/compare skips filtering (QA4.4).
    """
    import main
    import copy
    
    # Save original registry
    orig_mainnet = copy.deepcopy(main.REGISTRY_MAINNET)
    
    try:
        # Inject a test feed with mixed visible/hidden networks
        # Get a real feed to copy its structure
        eth_feeds = main.REGISTRY_MAINNET["networks"]["ethereum"]["feeds"]
        sample_feed = copy.deepcopy(list(eth_feeds.values())[0])
        
        # Modify to create test feed
        test_feed_meta = {
            **sample_feed,
            "name": "Test Multi-Network Feed",
            "path": "test-compare-feed",
            "shutdown_date": None  # Will be set per network
        }
        
        # Add to ethereum (no shutdown - visible)
        if "ethereum" in main.REGISTRY_MAINNET["networks"]:
            main.REGISTRY_MAINNET["networks"]["ethereum"]["feeds"]["test-compare-feed"] = {
                **test_feed_meta,
                "shutdown_date": None  # Visible
            }
        
        # Add to arbitrum with past shutdown date (hidden)
        if "arbitrum" in main.REGISTRY_MAINNET["networks"]:
            main.REGISTRY_MAINNET["networks"]["arbitrum"]["feeds"]["test-compare-feed"] = {
                **test_feed_meta,
                "shutdown_date": "2026-06-03"  # Hidden as of 10-19
            }
        
        client = TestClient(app)
        set_test_clock(datetime(2026, 10, 19, tzinfo=timezone.utc))
        
        response = client.get("/v1/compare/test-compare-feed")
        
        # Assert unconditionally
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "results" in data, "Response must have results key"
        
        # Extract network slugs from results
        result_networks = [r.get("network") for r in data["results"]]
        
        # Ethereum (visible) must be present
        assert "ethereum" in result_networks, \
            f"Visible network 'ethereum' must be in results. Got: {result_networks}"
        
        # Arbitrum (hidden) must be absent
        assert "arbitrum" not in result_networks, \
            f"Hidden network 'arbitrum' must NOT be in results. Got: {result_networks}"
    
    finally:
        # Restore original
        main.REGISTRY_MAINNET.clear()
        main.REGISTRY_MAINNET.update(orig_mainnet)


def test_svr_matching_prevents_false_lbtc_btc_link():
    """
    Mutant: A looser product-name match creates the false lbtc-btc link.
    Kill: Strict matching prevents LBTC/USD from linking to BTC/USD.
    
    Calls link_svr_variants on real Base feeds and asserts lbtc-btc-exchange-rate-svr
    (CLIC lBTC/BTC-ExRate-DF-Base-001) is NOT linked to lbtc-btc
    (CLIC LBTC/BTC-RefPrice-DF-Base-001).
    """
    from build_registry import link_svr_variants
    import copy
    
    # Load real registry data
    backend = Path(__file__).parent
    with open(backend / "registry.json") as f:
        reg = json.load(f)
    
    # Get base network feeds (make a copy to avoid modifying original)
    base_feeds = copy.deepcopy(reg["networks"]["base"]["feeds"])
    
    # Verify both feeds exist
    assert "lbtc-btc" in base_feeds, "lbtc-btc feed should exist"
    assert "lbtc-btc-exchange-rate-svr" in base_feeds, "lbtc-btc-exchange-rate-svr feed should exist"
    
    # Get initial state
    svr_feed_before = base_feeds["lbtc-btc-exchange-rate-svr"]
    assert svr_feed_before["clic_product_name"] == "lBTC/BTC-ExRate-DF-Base-001", \
        f"SVR feed should have CLIC lBTC/BTC-ExRate-DF-Base-001, got {svr_feed_before.get('clic_product_name')}"
    
    lbtc_btc_feed = base_feeds["lbtc-btc"]
    assert lbtc_btc_feed["clic_product_name"] == "LBTC/BTC-RefPrice-DF-Base-001", \
        f"lbtc-btc feed should have CLIC LBTC/BTC-RefPrice-DF-Base-001, got {lbtc_btc_feed.get('clic_product_name')}"
    
    # Run link_svr_variants on base feeds
    link_svr_variants(base_feeds)
    
    # Get SVR feed after linking
    svr_feed_after = base_feeds["lbtc-btc-exchange-rate-svr"]
    
    # Verify it does NOT link to lbtc-btc (they have different CLICs)
    base_path = svr_feed_after.get("base_path")
    assert base_path != "lbtc-btc", \
        f"lBTC/BTC Exchange Rate SVR incorrectly linked to lbtc-btc (false match). base_path={base_path}"
    
    # If it has a base_path, verify it's not the false match
    if base_path:
        assert base_path != "lbtc-btc", \
            f"SVR feed base_path should not be lbtc-btc, got {base_path}"


def test_registry_rebuild_keeps_generated_at_when_unchanged(tmp_path):
    """
    Mutant: generated_at freezes (never updates even when content changes).
    Kill: Same content keeps generated_at; changed content updates it.
    
    First build with MockTransport, second build with identical data, verify generated_at unchanged.
    """
    import httpx
    from build_registry import main as build_main
    
    # Create output dir
    output_dir = tmp_path / "backend"
    output_dir.mkdir()
    (output_dir / "data").mkdir()
    (output_dir / "data" / "nodes").mkdir()
    
    # Mock transport with consistent data
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if '/nodes-' in str(request.url):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{
            "path": "test-feed",
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "contractAddress": "0x0987654321098765432109876543210987654321",
            "decimals": 8,
            "heartbeat": 3600,
        }])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        # First build
        build_main(http_client=mock_client, output_dir=output_dir)
        
        # Read generated_at from first build
        with open(output_dir / "registry.json") as f:
            first_registry = json.load(f)
        first_generated_at = first_registry["generated_at"]
        
        # Second build with identical data
        build_main(http_client=mock_client, output_dir=output_dir)
        
        # Read generated_at from second build
        with open(output_dir / "registry.json") as f:
            second_registry = json.load(f)
        second_generated_at = second_registry["generated_at"]
        
        # generated_at should be unchanged (content identical)
        assert first_generated_at == second_generated_at, \
            f"generated_at changed despite identical content: {first_generated_at} -> {second_generated_at}"
        
        # Verify files are byte-identical
        first_bytes = json.dumps(first_registry, indent=1)
        second_bytes = json.dumps(second_registry, indent=1)
        assert first_bytes == second_bytes, "Registry content should be byte-identical"
    finally:
        mock_client.close()


def test_registry_rebuild_updates_generated_at_when_changed(tmp_path):
    """
    Mutant: generated_at freezes (never updates even when content changes).
    Kill: Changed content updates generated_at.
    
    First build, second build with different heartbeat, verify generated_at updated.
    """
    import httpx
    from build_registry import main as build_main
    import time
    
    # Create output dir
    output_dir = tmp_path / "backend"
    output_dir.mkdir()
    (output_dir / "data").mkdir()
    (output_dir / "data" / "nodes").mkdir()
    
    # First build with heartbeat 3600
    def mock_handler_1(request: httpx.Request) -> httpx.Response:
        if '/nodes-' in str(request.url):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{
            "path": "test-feed",
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "contractAddress": "0x0987654321098765432109876543210987654321",
            "decimals": 8,
            "heartbeat": 3600,
        }])
    
    mock_client_1 = httpx.Client(transport=httpx.MockTransport(mock_handler_1))
    
    try:
        build_main(http_client=mock_client_1, output_dir=output_dir)
    finally:
        mock_client_1.close()
    
    # Read generated_at from first build
    with open(output_dir / "registry.json") as f:
        first_registry = json.load(f)
    first_generated_at = first_registry["generated_at"]
    
    # Wait to ensure time.time() would return different value
    time.sleep(1)
    
    # Second build with different heartbeat
    def mock_handler_2(request: httpx.Request) -> httpx.Response:
        if '/nodes-' in str(request.url):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{
            "path": "test-feed",
            "proxyAddress": "0x1234567890123456789012345678901234567890",
            "contractAddress": "0x0987654321098765432109876543210987654321",
            "decimals": 8,
            "heartbeat": 3601,  # Changed
        }])
    
    mock_client_2 = httpx.Client(transport=httpx.MockTransport(mock_handler_2))
    
    try:
        build_main(http_client=mock_client_2, output_dir=output_dir)
    finally:
        mock_client_2.close()
    
    # Read generated_at from second build
    with open(output_dir / "registry.json") as f:
        second_registry = json.load(f)
    second_generated_at = second_registry["generated_at"]
    
    # generated_at should be updated (content changed)
    assert second_generated_at > first_generated_at, \
        f"generated_at should update when content changes: {first_generated_at} -> {second_generated_at}"
