"""
Production Mutation Tests - Call-Site Integration
=================================================
Tests that drive production checks through real builder entry points with
injected data to verify checks actually fail the build when thresholds are violated.
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest


def test_feed_count_check_fails_on_100_percent_drop():
    """
    Test that feed count check (via git HEAD comparison) detects 252->0 drop.
    
    Kills mutants:
    - feed-count call removed
    - check always passes  
    - wrong old/new order
    """
    import subprocess
    from build_registry import build_registry
    
    # Simulate git HEAD having 252 feeds
    committed_registry = {
        "version": "3.0.0",
        "environment": "mainnet",
        "networks": {
            "ethereum": {
                "feed_count": 252,
                "feeds": {}
            }
        }
    }
    
    def mock_run(*args, **kwargs):
        cmd = args[0] if args else []
        if isinstance(cmd, list) and "git" in str(cmd) and "show" in str(cmd):
            return Mock(returncode=0, stdout=json.dumps(committed_registry))
        return Mock(returncode=0, stdout="", stderr="")
    
    # Mock transport returning 0 feeds
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "backend"
            output_dir.mkdir()
            (output_dir / "data").mkdir()
            (output_dir / "data" / "nodes").mkdir()
            
            # Call build_registry with output_dir=None to trigger git-based check
            # But it will try to write to real backend dir, so we mock the write
            with patch('subprocess.run', side_effect=mock_run):
                # Should raise ValueError from check_feed_count_change before any writes
                with pytest.raises(ValueError, match="Feed count changed.*252.*0"):
                    from build_registry import MAINNET_CHAINS
                    build_registry(MAINNET_CHAINS, "mainnet", http_client=mock_client, output_dir=None)
    finally:
        mock_client.close()


def test_rpc_failure_rate_check_fails_on_41_percent():
    """
    Test that crawl_transmitters with 41% RPC failure fails.
    
    Kills mutants:
    - RPC check removed
    - threshold 30->100
    - wrong numerator/denominator
    """
    import build_operators
    from build_operators import REGISTRY_PATH, NODES_DIR, OVERRIDES_PATH
    
    registry = json.loads(REGISTRY_PATH.read_text())
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
    
    address_index, hidden_addresses = build_operators.build_address_index(NODES_DIR, overrides)
    
    # Precompute fixed set of failing feed addresses (41% of all feeds)
    all_feeds = []
    for net in registry["networks"].values():
        for path, feed in net["feeds"].items():
            if feed.get("aggregator"):
                all_feeds.append(feed["aggregator"].lower())
    
    all_feeds_sorted = sorted(all_feeds)
    fail_count = int(len(all_feeds_sorted) * 0.41)
    failing_addresses = set(all_feeds_sorted[:fail_count])
    
    # Encode a single dummy transmitter address for successful feeds
    success_result = "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000001111111111111111111111111111111111111111"
    
    # Mock transport: decide per address from request payload
    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json as json_module
        payload = json_module.loads(request.content)
        
        # Handle batch requests
        if isinstance(payload, list):
            responses = []
            for call in payload:
                to_address = call["params"][0]["to"].lower()
                if to_address in failing_addresses:
                    # This feed fails - return error
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "error": {"code": -32000, "message": "execution reverted"}
                    })
                else:
                    # This feed succeeds - return 1 transmitter
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "result": success_result
                    })
            return httpx.Response(200, json=responses)
        else:
            # Single request (fallback)
            to_address = payload["params"][0]["to"].lower()
            if to_address in failing_addresses:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "execution reverted"}
                })
            else:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "result": success_result
                })
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()  # Zero sleep
            
            # Mock the mapping rate check to always pass (we're testing RPC failure rate)
            with patch('refresh_checks.check_transmitter_mapping_rate'):
                # Should raise ValueError with ~41% rate
                with pytest.raises(ValueError) as exc_info:
                    build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides, http_client=mock_client)
                
                # Verify the reported rate is ~41% (allow 38-44%)
                error_msg = str(exc_info.value)
                import re
                match = re.search(r'RPC failure rate ([\d.]+)%', error_msg)
                assert match, f"Could not find failure rate in: {error_msg}"
                rate = float(match.group(1))
                assert 38 <= rate <= 44, f"Expected ~41% failure rate, got {rate}%"
    finally:
        mock_client.close()


def test_rpc_failure_rate_check_passes_below_threshold():
    """
    Test that crawl_transmitters with <30% RPC failure passes.
    
    Kills mutants:
    - threshold 30->50/99/100 (would cause this test to fail)
    """
    import build_operators
    from build_operators import REGISTRY_PATH, NODES_DIR, OVERRIDES_PATH
    
    registry = json.loads(REGISTRY_PATH.read_text())
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
    
    address_index, hidden_addresses = build_operators.build_address_index(NODES_DIR, overrides)
    
    # Precompute fixed set of failing feed addresses (~1% of all feeds)
    all_feeds = []
    for net in registry["networks"].values():
        for path, feed in net["feeds"].items():
            if feed.get("aggregator"):
                all_feeds.append(feed["aggregator"].lower())
    
    all_feeds_sorted = sorted(all_feeds)
    fail_count = max(1, int(len(all_feeds_sorted) * 0.01))
    failing_addresses = set(all_feeds_sorted[:fail_count])
    
    success_result = "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000001111111111111111111111111111111111111111"
    
    # Mock transport: decide per address
    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json as json_module
        payload = json_module.loads(request.content)
        
        if isinstance(payload, list):
            responses = []
            for call in payload:
                to_address = call["params"][0]["to"].lower()
                if to_address in failing_addresses:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "error": {"code": -32000, "message": "execution reverted"}
                    })
                else:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "result": success_result
                    })
            return httpx.Response(200, json=responses)
        else:
            to_address = payload["params"][0]["to"].lower()
            if to_address in failing_addresses:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "execution reverted"}
                })
            else:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "result": success_result
                })
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()
            
            # Mock the mapping rate check to always pass
            with patch('refresh_checks.check_transmitter_mapping_rate'):
                # Should NOT raise (1% < 30%)
                feed_ops = build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides, http_client=mock_client)
                assert feed_ops is not None
    finally:
        mock_client.close()


def test_rpc_failure_rate_check_just_above_threshold():
    """
    Test that 31% RPC failure (just above 30% threshold) fails.
    
    Kills mutants:
    - threshold 30->35/40/50 (would cause this test to pass incorrectly)
    """
    import build_operators
    from build_operators import REGISTRY_PATH, NODES_DIR, OVERRIDES_PATH
    
    registry = json.loads(REGISTRY_PATH.read_text())
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
    
    address_index, hidden_addresses = build_operators.build_address_index(NODES_DIR, overrides)
    
    # Precompute 31% failing addresses
    all_feeds = []
    for net in registry["networks"].values():
        for path, feed in net["feeds"].items():
            if feed.get("aggregator"):
                all_feeds.append(feed["aggregator"].lower())
    
    all_feeds_sorted = sorted(all_feeds)
    fail_count = int(len(all_feeds_sorted) * 0.31)
    failing_addresses = set(all_feeds_sorted[:fail_count])
    
    success_result = "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000001111111111111111111111111111111111111111"
    
    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json as json_module
        payload = json_module.loads(request.content)
        
        if isinstance(payload, list):
            responses = []
            for call in payload:
                to_address = call["params"][0]["to"].lower()
                if to_address in failing_addresses:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "error": {"code": -32000, "message": "execution reverted"}
                    })
                else:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "result": success_result
                    })
            return httpx.Response(200, json=responses)
        else:
            to_address = payload["params"][0]["to"].lower()
            if to_address in failing_addresses:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "execution reverted"}
                })
            else:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "result": success_result
                })
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()
            
            # Mock the mapping rate check to always pass
            with patch('refresh_checks.check_transmitter_mapping_rate'):
                # Should raise (31% > 30%)
                with pytest.raises(ValueError) as exc_info:
                    build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides, http_client=mock_client)
                
                # Verify rate is ~31%
                error_msg = str(exc_info.value)
                import re
                match = re.search(r'RPC failure rate ([\d.]+)%', error_msg)
                assert match, f"Could not find failure rate in: {error_msg}"
                rate = float(match.group(1))
                assert 29 <= rate <= 33, f"Expected ~31% failure rate, got {rate}%"
    finally:
        mock_client.close()


def test_rpc_failure_rate_check_exactly_at_threshold():
    """
    Test that exactly 30% RPC failure passes (boundary case).
    
    Kills mutants:
    - threshold check > changed to >= (would cause this to fail)
    """
    import build_operators
    from build_operators import REGISTRY_PATH, NODES_DIR, OVERRIDES_PATH
    
    registry = json.loads(REGISTRY_PATH.read_text())
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
    
    address_index, hidden_addresses = build_operators.build_address_index(NODES_DIR, overrides)
    
    # Precompute exactly 30% failing addresses
    all_feeds = []
    for net in registry["networks"].values():
        for path, feed in net["feeds"].items():
            if feed.get("aggregator"):
                all_feeds.append(feed["aggregator"].lower())
    
    all_feeds_sorted = sorted(all_feeds)
    fail_count = int(len(all_feeds_sorted) * 0.30)
    failing_addresses = set(all_feeds_sorted[:fail_count])
    
    success_result = "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000001111111111111111111111111111111111111111"
    
    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json as json_module
        payload = json_module.loads(request.content)
        
        if isinstance(payload, list):
            responses = []
            for call in payload:
                to_address = call["params"][0]["to"].lower()
                if to_address in failing_addresses:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "error": {"code": -32000, "message": "execution reverted"}
                    })
                else:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "result": success_result
                    })
            return httpx.Response(200, json=responses)
        else:
            to_address = payload["params"][0]["to"].lower()
            if to_address in failing_addresses:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "execution reverted"}
                })
            else:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "result": success_result
                })
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()
            
            # Mock the mapping rate check to always pass
            with patch('refresh_checks.check_transmitter_mapping_rate'):
                # Should NOT raise (30% == threshold, not >)
                feed_ops = build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides, http_client=mock_client)
                assert feed_ops is not None
    finally:
        mock_client.close()


def test_rpc_failure_whole_batch_fails():
    """
    Test that whole-batch HTTP failures (non-200 status) are counted correctly.
    
    Kills mutants:
    - batch counted as 1 failure instead of batch_size failures
    - batch failures not counted
    """
    import build_operators
    from build_operators import REGISTRY_PATH, NODES_DIR, OVERRIDES_PATH
    
    registry = json.loads(REGISTRY_PATH.read_text())
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
    
    address_index, hidden_addresses = build_operators.build_address_index(NODES_DIR, overrides)
    
    # Precompute exactly 40% of feed aggregators to fail
    all_feed_aggregators = []
    for net in registry["networks"].values():
        for path, feed in net["feeds"].items():
            if feed.get("aggregator"):
                all_feed_aggregators.append(feed["aggregator"].lower())
    
    fail_count = int(len(all_feed_aggregators) * 0.40)
    failing_aggregators = set(sorted(all_feed_aggregators)[:fail_count])
    
    success_result = "0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000001111111111111111111111111111111111111111"
    
    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json as json_module
        payload = json_module.loads(request.content)
        
        # Check if this batch contains any failing aggregators
        if isinstance(payload, list):
            # Check the first call's "to" address
            first_to = payload[0]["params"][0]["to"].lower()
            if first_to in failing_aggregators:
                # Whole batch fails at HTTP level
                return httpx.Response(500, text="Internal Server Error")
            else:
                # Batch succeeds
                responses = []
                for call in payload:
                    responses.append({
                        "id": call["id"],
                        "jsonrpc": "2.0",
                        "result": success_result
                    })
                return httpx.Response(200, json=responses)
        else:
            # Single request
            to_address = payload["params"][0]["to"].lower()
            if to_address in failing_aggregators:
                return httpx.Response(500, text="Internal Server Error")
            else:
                return httpx.Response(200, json={
                    "id": payload["id"],
                    "jsonrpc": "2.0",
                    "result": success_result
                })
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()
            
            # Mock the mapping rate check to always pass
            with patch('refresh_checks.check_transmitter_mapping_rate'):
                # Should raise (40% > 30%)
                try:
                    result = build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides, http_client=mock_client)
                    # If we get here, no exception was raised - test should fail
                    pytest.fail(f"Expected ValueError from check_rpc_failure_rate but got result with {len(result)} networks, total_feeds={total_feeds}, fail_count={fail_count}")
                except ValueError as e:
                    # This is expected
                    error_msg = str(e)
                    import re
                    match = re.search(r'RPC failure rate ([\d.]+)%', error_msg)
                    assert match, f"Could not find failure rate in: {error_msg}"
                    rate = float(match.group(1))
                    assert 37 <= rate <= 43, f"Expected ~40% failure rate, got {rate}%"
    finally:
        mock_client.close()


def test_mapping_rate_check_fails_below_98_percent():
    """
    Test that crawl_transmitters with <98% mapping rate fails.
    
    Kills mutants:
    - mapping-rate call removed
    - hidden not excluded from denominator
    - threshold 98->0
    """
    import build_operators
    
    # Create minimal test setup
    registry = {
        "networks": {
            "ethereum": {
                "label": "Ethereum",
                "feeds": {
                    "eth-usd": {
                        "aggregator": "0xaaa",
                        "name": "ETH/USD"
                    }
                },
                "rpc_urls": ["http://localhost"]
            }
        }
    }
    
    # 100 transmitters, only 97 mapped (97% < 98%)
    transmitters = [f"0x{i:040x}" for i in range(100)]
    address_index = {transmitters[i]: f"op{i}" for i in range(97)}  # Only 97 mapped
    hidden_addresses = set()
    overrides = {"hidden_patterns": []}
    
    # Encode transmitters like the real RPC does
    # Format: 0x + offset (32 bytes) + length (32 bytes) + addresses
    def encode_addresses(addrs):
        offset = "0000000000000000000000000000000000000000000000000000000000000020"  # offset to array
        length = f"{len(addrs):064x}"  # array length
        data = "".join(addr[2:].zfill(64) for addr in addrs)  # addresses without 0x
        return f"0x{offset}{length}{data}"
    
    # Mock returns proper JSON-RPC batch response
    mock_result = [{
        "id": 0,
        "jsonrpc": "2.0",
        "result": encode_addresses(transmitters)
    }]
    
    mock_client = Mock()
    mock_client.post.return_value = Mock(status_code=200, json=Mock(return_value=mock_result))
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    
    with patch.object(build_operators, 'httpx') as mock_httpx:
        mock_httpx.Client.return_value = mock_client
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="mapping rate.*97.*98"):
                build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides)


def test_check_rdd_response_codes_fails_on_404():
    """
    Test that RDD URL 404 responses fail the build.
    
    Kills mutants:
    - raise_for_status removed
    - check_rdd_response_codes call removed (still tested via raise_for_status)
    - check always passes
    """
    from build_registry import main as build_main
    
    # Mock transport returning 404 for feeds URL
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if 'feeds' in str(request.url):
            return httpx.Response(404, json={})
        return httpx.Response(200, json=[])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "backend"
            output_dir.mkdir()
            (output_dir / "data").mkdir()
            (output_dir / "data" / "nodes").mkdir()
            
            # Should raise HTTPStatusError (raise_for_status catches 404)
            with pytest.raises(httpx.HTTPStatusError, match="404"):
                build_main(http_client=mock_client, output_dir=output_dir)
    finally:
        mock_client.close()


def test_check_rdd_response_codes_collects_all_failures():
    """
    Test that check_rdd_response_codes is called after all fetches and reports all non-200s.
    
    Kills mutants:
    - check_rdd_response_codes call removed
    - check only validates first URL
    - check ignores nodes URLs
    """
    from build_registry import build_registry, MAINNET_CHAINS
    import refresh_checks
    
    # Mock check_rdd_response_codes to capture what it receives
    captured_responses = []
    original_check = refresh_checks.check_rdd_response_codes
    
    def mock_check(responses):
        captured_responses.append(responses)
        # Call original to ensure real validation
        original_check(responses)
    
    # Mock transport: return 200 for everything
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "backend"
            output_dir.mkdir()
            (output_dir / "data").mkdir()
            (output_dir / "data" / "nodes").mkdir()
            
            with patch.object(refresh_checks, 'check_rdd_response_codes', side_effect=mock_check):
                registry, total, temp_dir = build_registry(
                    MAINNET_CHAINS,
                    "mainnet",
                    http_client=mock_client,
                    output_dir=output_dir
                )
            
            # Verify check_rdd_response_codes was called
            assert len(captured_responses) > 0, "check_rdd_response_codes was never called"
            
            # Verify it received all feed + node URLs (13 mainnet chains × 2 = 26 URLs)
            responses = captured_responses[0]
            assert len(responses) >= 26, f"Expected at least 26 URLs, got {len(responses)}"
            
            # Verify all were 200
            assert all(code == 200 for code in responses.values()), "Not all responses were 200"
    finally:
        mock_client.close()


def test_check_hidden_operators_fails_on_leak():
    """
    Test that check_hidden_operators is called and fails when public operator matches pattern.
    
    Kills mutants:
    - check_hidden_operators call removed
    - should_hide_operator never filters
    """
    import build_operators
    
    # Create operator data with hidden pattern in public operator
    with tempfile.TemporaryDirectory() as tmpdir:
        nodes_dir = Path(tmpdir) / "nodes"
        nodes_dir.mkdir()
        
        # Create node with hidden pattern that should be filtered
        nodes = [{
            "id": "cl-ocr-nav-test",  # Hidden pattern
            "name": "Test Node",
            "nodeAddress": ["0x1111111111111111111111111111111111111111"]
        }]
        (nodes_dir / "nodes-mainnet.json").write_text(json.dumps(nodes))
        
        feed_operators = {
            "ethereum": {
                "eth-usd": {
                    "aggregator": "0xaaa",
                    "transmitters": ["0x1111111111111111111111111111111111111111"],
                    "operators": ["cl-ocr-nav-test"]
                }
            }
        }
        
        registry = {"networks": {"ethereum": {"feeds": {"eth-usd": {}}}}}
        overrides = {"hidden_patterns": ["cl-ocr-nav-"]}
        
        # Should raise ValueError (hidden operator leaked as public)
        with pytest.raises(ValueError, match="hidden pattern"):
            build_operators.build_operators_dataset(feed_operators, nodes_dir, overrides, registry)


def test_hidden_operators_excluded_from_mapping_rate():
    """
    Test that hidden operators are excluded from both numerator and denominator.
    
    Kills mutants:
    - hidden not subtracted from total
    - hidden counted in mapped
    - hidden not excluded from numerator
    """
    import build_operators
    
    registry = {
        "networks": {
            "ethereum": {
                "label": "Ethereum",
                "feeds": {
                    "eth-usd": {"aggregator": "0xaaa"}
                },
                "rpc_urls": ["http://localhost"]
            }
        }
    }
    
    # 100 transmitters: 80 public (all mapped), 20 hidden
    public_transmitters = [f"0x1{i:039x}" for i in range(80)]
    hidden_transmitters = [f"0x2{i:039x}" for i in range(20)]
    all_transmitters = public_transmitters + hidden_transmitters
    
    address_index = {addr: f"op{i}" for i, addr in enumerate(public_transmitters)}
    hidden_addresses = set(hidden_transmitters)
    overrides = {"hidden_patterns": []}
    
    # Encode transmitters like the real RPC does
    def encode_addresses(addrs):
        offset = "0000000000000000000000000000000000000000000000000000000000000020"
        length = f"{len(addrs):064x}"
        data = "".join(addr[2:].zfill(64) for addr in addrs)
        return f"0x{offset}{length}{data}"
    
    # Mock returns proper JSON-RPC batch response
    mock_result = [{
        "id": 0,
        "jsonrpc": "2.0",
        "result": encode_addresses(all_transmitters)
    }]
    
    mock_client = Mock()
    mock_client.post.return_value = Mock(status_code=200, json=Mock(return_value=mock_result))
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    
    with patch.object(build_operators, 'httpx') as mock_httpx:
        mock_httpx.Client.return_value = mock_client
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()
            
            # Should NOT raise (80/80 = 100% of public operators mapped)
            feed_ops = build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides)
            assert feed_ops is not None
            
            # Verify hidden operators are NOT in the operators list
            eth_feed = feed_ops["ethereum"]["eth-usd"]
            assert len(eth_feed["operators"]) == 80, "Should only count public operators"
            assert len(eth_feed["transmitters"]) == 80, "Should only list public transmitters (hidden filtered)"


def test_hidden_address_index_excludes_patterns():
    """
    Test that build_address_index correctly identifies and excludes hidden operators.
    
    Kills mutants:
    - hidden_patterns not applied
    - hidden addresses returned in public index
    """
    import build_operators
    
    with tempfile.TemporaryDirectory() as tmpdir:
        nodes_dir = Path(tmpdir) / "nodes"
        nodes_dir.mkdir()
        
        # Create nodes with mix of public and hidden operators
        nodes = [
            {
                "id": "public-op-1",
                "name": "Public Operator 1",
                "nodeAddress": ["0x1111111111111111111111111111111111111111"]
            },
            {
                "id": "cl-ocr-nav-test",  # Matches hidden pattern
                "name": "Hidden Test Node",
                "nodeAddress": ["0x2222222222222222222222222222222222222222"]
            },
            {
                "id": "public-op-2",
                "name": "Public Operator 2",
                "nodeAddress": ["0x3333333333333333333333333333333333333333"]
            }
        ]
        (nodes_dir / "nodes-mainnet.json").write_text(json.dumps(nodes))
        
        overrides = {"hidden_patterns": ["cl-ocr-nav-"]}
        
        address_index, hidden_addresses = build_operators.build_address_index(nodes_dir, overrides)
        
        # Public addresses should be in the index
        assert "0x1111111111111111111111111111111111111111" in address_index
        assert "0x3333333333333333333333333333333333333333" in address_index
        
        # Hidden address should NOT be in public index
        assert "0x2222222222222222222222222222222222222222" not in address_index
        
        # Hidden address should be in hidden set
        assert "0x2222222222222222222222222222222222222222" in hidden_addresses


def test_case_insensitive_operator_matching():
    """
    Test that operator aggregation uses case-insensitive matching.
    
    Kills mutants:
    - slugs not lowercased
    """
    import build_operators
    
    with tempfile.TemporaryDirectory() as tmpdir:
        nodes_dir = Path(tmpdir) / "nodes"
        nodes_dir.mkdir()
        
        # Node with mixed-case ID
        nodes = [{
            "id": "LinkPool",
            "name": "LinkPool",
            "website": "https://linkpool.io",
            "nodeAddress": ["0x1111111111111111111111111111111111111111"]
        }]
        (nodes_dir / "nodes-mainnet.json").write_text(json.dumps(nodes))
        
        # Feed operators with lowercase slug
        feed_operators = {
            "ethereum": {
                "eth-usd": {
                    "aggregator": "0xaaa",
                    "transmitters": ["0x1111111111111111111111111111111111111111"],
                    "operators": ["linkpool"]  # Lowercase
                }
            }
        }
        
        registry = {"networks": {"ethereum": {"feeds": {"eth-usd": {}}}}}
        overrides = {"hidden_patterns": []}
        
        result = build_operators.build_operators_dataset(feed_operators, nodes_dir, overrides, registry)
        
        # Should find the operator and populate its data
        assert len(result["operators"]) == 1
        op = result["operators"][0]
        assert op["slug"] == "linkpool"
        assert op["name"] == "LinkPool"
        assert op["website"] == "https://linkpool.io"
        assert len(op.get("rdd_ids", {})) > 0


def test_rdd_ids_populated_from_nodes():
    """
    Test that rdd_ids are populated from nodes files (not forced null).
    
    Kills mutants:
    - rdd_ids forced null
    - rdd_ids empty always
    """
    import build_operators
    
    with tempfile.TemporaryDirectory() as tmpdir:
        nodes_dir = Path(tmpdir) / "nodes"
        nodes_dir.mkdir()
        
        nodes = [{
            "id": "testop",
            "name": "Test Operator",
            "nodeAddress": ["0x2222222222222222222222222222222222222222"]
        }]
        (nodes_dir / "nodes-mainnet.json").write_text(json.dumps(nodes))
        
        feed_operators = {
            "ethereum": {
                "test-usd": {
                    "aggregator": "0xbbb",
                    "transmitters": ["0x2222222222222222222222222222222222222222"],
                    "operators": ["testop"]
                }
            }
        }
        
        registry = {"networks": {"ethereum": {"feeds": {"test-usd": {}}}}}
        overrides = {"hidden_patterns": []}
        
        result = build_operators.build_operators_dataset(feed_operators, nodes_dir, overrides, registry)
        
        op = result["operators"][0]
        assert op["rdd_ids"] is not None, "rdd_ids should not be null"
        assert "ethereum" in op["rdd_ids"]
        assert "testop" in op["rdd_ids"]["ethereum"]


def test_addresses_sorted_deterministically():
    """
    Test that addresses are sorted for deterministic output.
    
    Kills mutants:
    - address sort removed
    """
    import build_operators
    
    with tempfile.TemporaryDirectory() as tmpdir:
        nodes_dir = Path(tmpdir) / "nodes"
        nodes_dir.mkdir()
        
        nodes = [{
            "id": "testop",
            "name": "Test Operator",
            "nodeAddress": [
                "0xzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",  # Should be last
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"   # Should be first
            ]
        }]
        (nodes_dir / "nodes-mainnet.json").write_text(json.dumps(nodes))
        
        feed_operators = {
            "ethereum": {
                "test-usd": {
                    "aggregator": "0xbbb",
                    "transmitters": [
                        "0xzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
                        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    ],
                    "operators": ["testop"]
                }
            }
        }
        
        registry = {"networks": {"ethereum": {"feeds": {"test-usd": {}}}}}
        overrides = {"hidden_patterns": []}
        
        result = build_operators.build_operators_dataset(feed_operators, nodes_dir, overrides, registry)
        
        addresses = result["operators"][0]["addresses"]
        
        # Verify sorted
        for i in range(len(addresses) - 1):
            curr = (addresses[i]["network"], addresses[i]["kind"], addresses[i]["address"])
            next_addr = (addresses[i+1]["network"], addresses[i+1]["kind"], addresses[i+1]["address"])
            assert curr <= next_addr, f"Addresses not sorted: {curr} > {next_addr}"


def test_registry_json_deterministic_after_two_full_builds():
    """
    Test that running build_registry + build_operators twice produces byte-identical registry.json.
    
    Kills mutants:
    - generated_at always updated
    - comparison includes downstream fields (operator_count at feed level)
    - feed-level operator_count pop removed
    """
    import build_registry
    import build_operators
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "backend"
        output_dir.mkdir()
        data_dir = output_dir / "data"
        data_dir.mkdir()
        (data_dir / "nodes").mkdir()
        
        # Create minimal nodes file
        nodes = [{
            "id": "testop",
            "name": "Test Operator",
            "nodeAddress": ["0x1111111111111111111111111111111111111111"]
        }]
        (data_dir / "nodes" / "nodes-mainnet.json").write_text(json.dumps(nodes))
        
        # Mock transport returning one real feed
        feed_data = {
            "path": "eth-usd",
            "name": "ETH / USD",
            "proxyAddress": "0x" + "a" * 40,
            "contractAddress": "0x" + "b" * 40,
            "decimals": 8,
            "heartbeat": 3600,
        }
        
        def mock_handler(request: httpx.Request) -> httpx.Response:
            if 'nodes-' in str(request.url):
                return httpx.Response(200, json=nodes)
            return httpx.Response(200, json=[feed_data])
        
        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        
        # Patch time.time to return strictly increasing values
        # This ensures determinism test fails even when builds are fast
        current_time = [1000000]
        
        def mock_time():
            current_time[0] += 10  # Advance by 10 seconds each call
            return current_time[0]
        
        try:
            with patch('time.time', side_effect=mock_time):
                # First build cycle: build_registry
                build_registry.main(http_client=mock_client, output_dir=output_dir)
                registry_path = output_dir / "registry.json"
                
                # Simulate build_operators adding operator_count to each feed
                r1 = json.loads(registry_path.read_text())
                for net in r1["networks"].values():
                    for feed in net["feeds"].values():
                        feed["operator_count"] = 1  # Feed-level operator_count
                registry_path.write_text(json.dumps(r1, indent=1) + "\n")
                first_generated_at = r1["generated_at"]
                
                # Second build cycle: build_registry should preserve generated_at
                build_registry.main(http_client=mock_client, output_dir=output_dir)
                r2 = json.loads(registry_path.read_text())
                
                # Simulate build_operators adding operator_count again
                for net in r2["networks"].values():
                    for feed in net["feeds"].values():
                        feed["operator_count"] = 1
                registry_path.write_text(json.dumps(r2, indent=1) + "\n")
                second_generated_at = r2["generated_at"]
                
                # Third cycle to verify stability
                build_registry.main(http_client=mock_client, output_dir=output_dir)
                r3 = json.loads(registry_path.read_text())
                for net in r3["networks"].values():
                    for feed in net["feeds"].values():
                        feed["operator_count"] = 1
                registry_path.write_text(json.dumps(r3, indent=1) + "\n")
                third_generated_at = r3["generated_at"]
                
                # All three should have same generated_at (no content change)
                assert first_generated_at == second_generated_at == third_generated_at, \
                    f"generated_at changed: {first_generated_at} -> {second_generated_at} -> {third_generated_at}"
                
                # Files should be byte-identical
                r1_bytes = json.dumps(r1, indent=1) + "\n"
                r2_bytes = json.dumps(r2, indent=1) + "\n"
                r3_bytes = json.dumps(r3, indent=1) + "\n"
                assert r1_bytes == r2_bytes == r3_bytes, "Registry file not byte-identical"
        finally:
            mock_client.close()
