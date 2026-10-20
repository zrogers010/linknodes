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
    Test that build_registry with 252->0 feed count fails.
    
    Kills mutants:
    - feed-count call removed
    - check always passes  
    - wrong old/new order
    """
    import subprocess
    from build_registry import main as build_main
    
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
        # Git config calls should succeed
        return Mock(returncode=0, stdout="", stderr="")
    
    # Mock transport returning 0 feeds
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])
    
    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    
    try:
        # Use production mode (output_dir=None) to trigger git-based checks
        with patch('subprocess.run', side_effect=mock_run):
            # Should raise ValueError from check_feed_count_change
            with pytest.raises(ValueError, match="Feed count changed.*252.*0"):
                build_main(http_client=mock_client, output_dir=None)
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
    
    # Count total attempted feeds
    total_attempted = sum(
        len([f for f in net["feeds"].values() if f.get("aggregator")])
        for net in registry["networks"].values()
    )
    
    # Mock to fail 41% of batches
    fail_count = int(total_attempted * 0.41) + 1
    call_count = [0]
    
    def mock_post(*args, **kwargs):
        call_count[0] += 1
        # Each batch is 10 feeds, count by batches
        batch_num = (call_count[0] - 1) // 1  # Simplified
        if batch_num * 10 < fail_count:
            raise Exception("RPC failure")
        return Mock(status_code=200, json=Mock(return_value=[]))
    
    mock_client = Mock()
    mock_client.post = mock_post
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    
    with patch.object(build_operators, 'httpx') as mock_httpx:
        mock_httpx.Client.return_value = mock_client
        with patch.object(build_operators, 'time') as mock_time:
            mock_time.time.return_value = 0
            mock_time.sleep = Mock()  # No-op for speed
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="RPC failure rate.*30"):
                build_operators.crawl_transmitters(registry, address_index, hidden_addresses, overrides)


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
    - check_rdd_response_codes call removed
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
    - comparison includes downstream fields
    """
    import build_registry
    import build_operators
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "backend"
        output_dir.mkdir()
        data_dir = output_dir / "data"
        data_dir.mkdir()
        (data_dir / "nodes").mkdir()
        
        # Mock transport returning empty feeds
        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[])
        
        mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
        
        try:
            # First build cycle
            build_registry.main(http_client=mock_client, output_dir=output_dir)
            # build_operators would normally add operator_count, simulate it
            registry_path = output_dir / "registry.json"
            r1 = json.loads(registry_path.read_text())
            for net in r1["networks"].values():
                net["operator_count"] = 0
            registry_path.write_text(json.dumps(r1, indent=1) + "\n")
            
            # Second build cycle
            build_registry.main(http_client=mock_client, output_dir=output_dir)
            r2 = json.loads(registry_path.read_text())
            for net in r2["networks"].values():
                net["operator_count"] = 0
            registry_path.write_text(json.dumps(r2, indent=1) + "\n")
            
            # Compare
            r1_bytes = registry_path.read_bytes()
            
            # Third cycle to verify still stable
            build_registry.main(http_client=mock_client, output_dir=output_dir)
            r3 = json.loads(registry_path.read_text())
            for net in r3["networks"].values():
                net["operator_count"] = 0
            registry_path.write_text(json.dumps(r3, indent=1) + "\n")
            
            r2_bytes = registry_path.read_bytes()
            
            # Should be byte-identical (same generated_at)
            assert r1 == r2 == r3, "Registry changed between builds with no upstream changes"
            assert r1_bytes == r2_bytes, "Registry file not byte-identical"
        finally:
            mock_client.close()
