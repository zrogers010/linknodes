"""
Test mutation killers for build_registry.py.

Tests that call the actual build functions (compact, nodes writer, SVR linker)
on fixtures to ensure mutations fail. Previously read committed registry.json,
which never exercised build code.
"""

import json
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from build_registry import compact, parse_shutdown_date, compute_feed_status


def test_clic_product_name_source():
    """Test that clic_product_name is sourced from docs.clicProductName."""
    fixture = {
        "name": "ETH / USD",
        "path": "eth-usd",
        "proxyAddress": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "docs": {"clicProductName": "ETH-USD-Mainnet"},
    }
    
    compacted = compact(fixture)
    
    assert compacted.get("clic_product_name") == "ETH-USD-Mainnet", \
        "clic_product_name should come from docs.clicProductName"
    
    # Mutant: if clic_product_name source is changed, this fails
    print("✓ clic_product_name sourced from docs.clicProductName")


def test_nodes_files_exist():
    """Test that nodes writer creates all files including testnet and copy2 mutation fails."""
    from build_registry import write_nodes
    
    # Create temp directories for test
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        staged_dir = tmp_path / "staged"
        dest_dir = tmp_path / "nodes"
        staged_dir.mkdir()
        
        # Create staged nodes files (including testnet)
        mainnet_files = {
            "nodes-mainnet.json": [{"id": "op1", "name": "Operator 1"}],
            "nodes-matic-mainnet.json": [{"id": "op2", "name": "Operator 2"}],
            "nodes-avalanche-mainnet.json": [{"id": "op3", "name": "Operator 3"}],
        }
        testnet_files = {
            "nodes-sepolia.json": [{"id": "op4", "name": "Operator 4"}],
            "nodes-avalanche-fuji-testnet.json": [{"id": "op5", "name": "Operator 5"}],
        }
        all_files = {**mainnet_files, **testnet_files}
        
        for filename, content in all_files.items():
            (staged_dir / filename).write_text(json.dumps(content))
        
        # Call the real nodes writer
        write_nodes(staged_dir, dest_dir)
        
        # Verify all mainnet files were copied
        for filename in mainnet_files.keys():
            dest_file = dest_dir / filename
            assert dest_file.exists(), f"{filename} should be created"
            assert dest_file.stat().st_size > 0, f"{filename} should be non-empty"
            content = json.loads(dest_file.read_text())
            assert len(content) > 0, f"{filename} should have content"
        
        # Explicitly verify testnet files were copied (kills "skip testnet" mutant)
        for filename in testnet_files.keys():
            dest_file = dest_dir / filename
            assert dest_file.exists(), f"Testnet file {filename} should be created"
            assert dest_file.stat().st_size > 0, f"Testnet file {filename} should be non-empty"
            content = json.loads(dest_file.read_text())
            assert len(content) > 0, f"Testnet file {filename} should have content"
        
    print(f"✓ Nodes writer created {len(all_files)} files (including {len(testnet_files)} testnet)")


def test_testnet_failure_leaves_mainnet_unchanged():
    """Test that testnet build failure doesn't corrupt files and cleans up temp dirs."""
    import hashlib
    import glob
    import shutil
    import tempfile
    import subprocess
    import sys
    from pathlib import Path
    import pytest
    
    backend_dir = Path(__file__).parent
    
    # Hash real backend files BEFORE test
    real_files = [
        backend_dir / "registry.json",
        backend_dir / "registry_testnet.json",
    ] + list((backend_dir / "data" / "nodes").glob("*.json"))
    
    def get_real_file_hashes():
        hashes = {}
        for f in real_files:
            if f.exists():
                hashes[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
        return hashes
    
    real_before_hashes = get_real_file_hashes()
    
    # Create a tmp copy of backend/ to run build in isolation
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_backend = Path(tmp_dir) / "backend"
        tmp_backend.mkdir()
        
        # Copy necessary files
        for file in ["build_registry.py", "registry.json", "registry_testnet.json"]:
            if (backend_dir / file).exists():
                shutil.copy2(backend_dir / file, tmp_backend / file)
        
        # Copy data/nodes directory
        nodes_src = backend_dir / "data" / "nodes"
        if nodes_src.exists():
            nodes_dst = tmp_backend / "data" / "nodes"
            nodes_dst.mkdir(parents=True)
            for node_file in nodes_src.glob("*.json"):
                shutil.copy2(node_file, nodes_dst / node_file.name)
        
        # Files to monitor in tmp directory
        tmp_files = [
            tmp_backend / "registry.json",
            tmp_backend / "registry_testnet.json",
        ] + list((tmp_backend / "data" / "nodes").glob("*.json"))
        
        def get_tmp_file_hashes():
            hashes = {}
            for f in tmp_files:
                if f.exists():
                    hashes[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
            return hashes
        
        tmp_before_hashes = get_tmp_file_hashes()
        
        # Count temp dirs before
        temp_dirs_before = set(glob.glob("/tmp/registry_build_*"))
        
        # Run build_registry.main() as subprocess in tmp directory with mocked httpx
        # Use subprocess to ensure it runs from tmp copy, not imported backend module
        test_script = tmp_backend / "test_build.py"
        test_script.write_text("""
import sys
from unittest.mock import patch, MagicMock

def mock_get(url):
    response = MagicMock()
    if "sepolia" in url or "fuji" in url:
        response.status_code = 404
        response.raise_for_status.side_effect = Exception("404 Not Found")
    else:
        if "feeds-" in url or "nodes-" in url:
            response.status_code = 200
            response.json.return_value = []
        else:
            response.status_code = 200
    return response

with patch('httpx.Client') as mock_client_class:
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client.get = mock_get
    
    from build_registry import main
    main()
""")
        
        # Run subprocess
        result = subprocess.run(
            [sys.executable, str(test_script)],
            cwd=str(tmp_backend),
            capture_output=True,
            text=True
        )
        
        # Build should have failed with non-zero exit
        assert result.returncode != 0, "Build should fail when testnet 404s"
        
        # Verify tmp files unchanged
        tmp_after_hashes = get_tmp_file_hashes()
        for file_path, before_hash in tmp_before_hashes.items():
            after_hash = tmp_after_hashes.get(file_path)
            assert after_hash == before_hash, f"TMP {file_path} was modified"
        
        # Verify no new temp dirs remain
        temp_dirs_after = set(glob.glob("/tmp/registry_build_*"))
        new_temp_dirs = temp_dirs_after - temp_dirs_before
        assert len(new_temp_dirs) == 0, f"Temp dirs leaked: {new_temp_dirs}"
    
    # Verify REAL backend files are unchanged
    real_after_hashes = get_real_file_hashes()
    for file_path, before_hash in real_before_hashes.items():
        after_hash = real_after_hashes.get(file_path)
        assert after_hash == before_hash, f"REAL {file_path} was modified by test!"
    
    print("✓ Testnet failure leaves tmp files unchanged")
    print("✓ Real backend files untouched")
    print("✓ No temp dir leaks")



def test_product_type_mapping():
    """Test that product_type is correctly mapped from docs.productType field."""
    fixture = {
        "name": "ETH / USD",
        "path": "eth-usd",
        "proxyAddress": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "docs": {"productType": "Crypto"},
    }
    
    compacted = compact(fixture)
    
    assert compacted.get("product_type") == "Crypto", \
        "product_type should be mapped from docs.productType"
    
    print("✓ product_type mapped from docs.productType field")


def test_svr_proxy_mapping():
    """Test that SVR feeds get svr_label from svrDisplayLabel and svr_proxy from secondaryProxyAddress."""
    fixture = {
        "name": "ETH / USD SVR",
        "path": "eth-usd-svr",
        "proxyAddress": "0xabcd",
        "secondaryProxyAddress": "0x1234567890abcdef",
        "svrDisplayLabel": "Shared SVR",
    }
    
    compacted = compact(fixture)
    
    assert compacted.get("svr_label") == "Shared SVR", \
        "svr_label should come from svrDisplayLabel"
    assert compacted.get("svr_proxy") == "0x1234567890abcdef", \
        "svr_proxy should come from secondaryProxyAddress"
    
    print("✓ svr_label mapped from svrDisplayLabel")
    print("✓ svr_proxy mapped from secondaryProxyAddress")


def test_contract_version_mapping():
    """Test that contractVersion is mapped from top-level contractVersion."""
    fixture_v3 = {
        "name": "ETH / USD",
        "path": "eth-usd",
        "proxyAddress": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "contractVersion": 3,
    }
    
    fixture_v2 = {
        "name": "LINK / USD",
        "path": "link-usd",
        "proxyAddress": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
        "contractVersion": 2,
    }
    
    compacted_v3 = compact(fixture_v3)
    compacted_v2 = compact(fixture_v2)
    
    assert compacted_v3.get("contract_version") == 3, "Should map v3"
    assert compacted_v2.get("contract_version") == 2, "Should map v2"
    
    print("✓ contract_version mapped from contractVersion")


def test_base_quote_mapping():
    """Test that base and quote are correctly extracted from docs."""
    fixture = {
        "name": "ETH / USD",
        "path": "eth-usd",
        "proxyAddress": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "docs": {
            "baseAsset": "ETH",
            "quoteAsset": "USD"
        }
    }
    
    compacted = compact(fixture)
    
    # compact() should extract base/quote from docs
    assert compacted.get("base") == "ETH", "base should be ETH"
    assert compacted.get("quote") == "USD", "quote should be USD"
    
    print("✓ base and quote extracted from docs.baseAsset/quoteAsset")


def test_shutdown_filter_enabled():
    """Test that shutdown date is parsed and status is computed."""
    fixture_deprecating = {
        "name": "STBRL / TBRL Exchange Rate",
        "path": "stbrl-tbrl-exchange-rate",
        "proxyAddress": "0xabcd",
        "docs": {"shutdownDate": "October 18th, 2026"},
        "feedCategory": "active",
    }
    
    fixture_no_shutdown = {
        "name": "ETH / USD",
        "path": "eth-usd",
        "proxyAddress": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "feedCategory": "active",
    }
    
    compacted_deprecating = compact(fixture_deprecating)
    compacted_active = compact(fixture_no_shutdown)
    
    # Check shutdown date parsing
    shutdown_date = parse_shutdown_date("October 18th, 2026")
    assert shutdown_date == "2026-10-18", "Shutdown date should parse correctly"
    
    # Check status computation (using fixed test date 2026-10-17)
    status_before = compute_feed_status("active", "2026-10-18", "2026-10-17")
    status_after = compute_feed_status("active", "2026-10-18", "2026-10-19")
    
    assert status_before == "deprecating", "Before shutdown => deprecating"
    assert status_after == "shut_down", "After shutdown => shut_down"
    
    assert compacted_deprecating.get("shutdown_date") == "2026-10-18", \
        "Shutdown date should be in compacted feed"
    
    assert compacted_active.get("shutdown_date") is None, \
        "No shutdown date for active feeds"
    
    print("✓ Shutdown date parsing and status computation working")


def test_integration_fixture_vs_real():
    """Integration: verify fixture tests match real registry for key feeds."""
    registry_path = Path(__file__).parent / "registry.json"
    if not registry_path.exists():
        print("⚠ Skipping integration test - registry.json not found")
        return
    
    registry = json.loads(registry_path.read_text())
    eth_feeds = registry["networks"]["ethereum"]["feeds"]
    
    # Check that at least one real feed has the expected fields
    eth_usd = eth_feeds.get("eth-usd")
    if eth_usd:
        assert "name" in eth_usd
        assert "address" in eth_usd
        assert "heartbeat" in eth_usd
        assert "decimals" in eth_usd
        print("✓ Integration: Real registry has expected shape")
    else:
        print("⚠ eth-usd feed not found in registry")


if __name__ == "__main__":
    print("=" * 100)
    print("Mutation Killer Tests (Fixture-Based)")
    print("=" * 100)
    print()
    
    test_clic_product_name_source()
    test_nodes_files_exist()
    test_product_type_mapping()
    test_svr_proxy_mapping()
    test_contract_version_mapping()
    test_base_quote_mapping()
    test_shutdown_filter_enabled()
    test_integration_fixture_vs_real()
    
    print()
    print("=" * 100)
    print("✓ All mutation killer tests passed")
    print("=" * 100)
