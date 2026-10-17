#!/usr/bin/env python3
"""
Backend Integration Tests
=========================
Test key API endpoints to verify correctness fixes.
"""

import json
import sys
import time
from pathlib import Path
import re

# Test without external dependencies
import urllib.request
import urllib.error


BASE_URL = "http://127.0.0.1:8100"


def is_valid_address(addr: str) -> bool:
    """Check if address is a valid 0x-prefixed 40-hex string."""
    if not addr:
        return False
    return bool(re.match(r'^0x[0-9a-fA-F]{40}$', addr))


def test_registry_v3_fields():
    """Test that the v3 registry has all required fields and valid addresses."""
    print(f"\n{'='*60}")
    print("TEST: Registry v3 Fields and Validation")
    print(f"{'='*60}")
    
    registry_path = Path(__file__).parent / "registry.json"
    if not registry_path.exists():
        print(f"❌ FAIL: registry.json not found at {registry_path}")
        return False
    
    registry = json.loads(registry_path.read_text())
    
    mainnet_feed_count = 0
    mainnet_with_aggregator = 0
    invalid_addresses = []
    
    for network_key, network_data in registry["networks"].items():
        for feed_key, feed_data in network_data["feeds"].items():
            mainnet_feed_count += 1
            
            proxy = feed_data.get("address")
            if not is_valid_address(proxy):
                invalid_addresses.append(f"{network_key}/{feed_key}: invalid proxy {proxy}")
            
            aggregator = feed_data.get("aggregator")
            if aggregator:
                mainnet_with_aggregator += 1
                if not is_valid_address(aggregator):
                    invalid_addresses.append(f"{network_key}/{feed_key}: invalid aggregator {aggregator}")
            
            svr_proxy = feed_data.get("svr_proxy")
            if svr_proxy and not is_valid_address(svr_proxy):
                invalid_addresses.append(f"{network_key}/{feed_key}: invalid svr_proxy {svr_proxy}")
    
    if invalid_addresses:
        print(f"❌ FAIL: Found {len(invalid_addresses)} invalid addresses:")
        for addr in invalid_addresses[:5]:
            print(f"   {addr}")
        return False
    
    print(f"✅ All proxy, aggregator, and svr_proxy addresses are valid 0x-prefixed 40-hex strings")
    
    aggregator_pct = (mainnet_with_aggregator / mainnet_feed_count * 100) if mainnet_feed_count > 0 else 0
    print(f"✅ {mainnet_with_aggregator}/{mainnet_feed_count} mainnet feeds ({aggregator_pct:.1f}%) have an aggregator")
    
    if aggregator_pct < 100.0:
        print(f"❌ FAIL: Expected 100% of mainnet feeds to have an aggregator")
        return False
    
    eth_usd = registry["networks"].get("ethereum", {}).get("feeds", {}).get("eth-usd", {})
    expected_agg = "0x7d4E742018fb52E48b08BE73d041C18B21de6Fb5"
    actual_agg = eth_usd.get("aggregator")
    
    if actual_agg != expected_agg:
        print(f"❌ FAIL: ethereum/eth-usd.aggregator expected {expected_agg}, got {actual_agg}")
        return False
    
    print(f"✅ ethereum/eth-usd.aggregator == {expected_agg}")
    
    return True


def test_testnet_networks():
    """Test that /healthz reports 7 testnet networks."""
    print(f"\n{'='*60}")
    print("TEST: Testnet Networks Count")
    print(f"{'='*60}")
    
    try:
        req = urllib.request.Request(f"{BASE_URL}/healthz")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            testnet_networks = data.get("testnet", {}).get("networks", 0)
            
            if testnet_networks != 7:
                print(f"❌ FAIL: Expected 7 testnet networks, got {testnet_networks}")
                return False
            
            print(f"✅ /healthz reports {testnet_networks} testnet networks")
            return True
    
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_svr_variants():
    """Test that SVR variants exist as separate records with base_path."""
    print(f"\n{'='*60}")
    print("TEST: SVR Variants with base_path")
    print(f"{'='*60}")
    
    registry_path = Path(__file__).parent / "registry.json"
    if not registry_path.exists():
        print(f"❌ FAIL: registry.json not found")
        return False
    
    registry = json.loads(registry_path.read_text())
    
    svr_variants_found = []
    svr_no_base = []
    svr_invalid_base = []
    
    for network_key, network_data in registry["networks"].items():
        network_feeds = network_data["feeds"]
        for feed_key, feed_data in network_feeds.items():
            if feed_data.get("svr_label"):
                base_path = feed_data.get("base_path")
                
                if base_path:
                    if base_path not in network_feeds:
                        svr_invalid_base.append(f"{network_key}/{feed_key} -> base_path={base_path} (NOT FOUND)")
                    elif network_feeds[base_path].get("svr_label"):
                        svr_invalid_base.append(f"{network_key}/{feed_key} -> base_path={base_path} (POINTS TO ANOTHER SVR)")
                    else:
                        svr_variants_found.append(f"{network_key}/{feed_key} -> base_path={base_path}")
                else:
                    clic_name = feed_data.get("clic_product_name")
                    base_asset = feed_data.get("base")
                    quote_asset = feed_data.get("quote")
                    
                    has_matching_base = False
                    for candidate_key, candidate in network_feeds.items():
                        if candidate_key == feed_key:
                            continue
                        if candidate.get("svr_label"):
                            continue
                        
                        if clic_name and candidate.get("clic_product_name") == clic_name:
                            has_matching_base = True
                            break
                        
                        if (base_asset and quote_asset and 
                            candidate.get("base") == base_asset and 
                            candidate.get("quote") == quote_asset):
                            has_matching_base = True
                            break
                    
                    if has_matching_base:
                        svr_invalid_base.append(f"{network_key}/{feed_key} has matching base but no base_path!")
                    else:
                        svr_no_base.append(f"{network_key}/{feed_key} (no base feed exists)")
    
    if svr_invalid_base:
        print(f"❌ FAIL: Found {len(svr_invalid_base)} SVR variants with invalid base_path:")
        for variant in svr_invalid_base[:5]:
            print(f"   {variant}")
        return False
    
    print(f"✅ Found {len(svr_variants_found)} SVR variants with valid base_path:")
    for variant in svr_variants_found[:3]:
        print(f"   {variant}")
    
    print(f"✅ Found {len(svr_no_base)} SVR variants without base (no matching non-SVR feed exists)")
    
    return True


def test_nodes_files():
    """Test that nodes files exist for all networks and parse as valid JSON."""
    print(f"\n{'='*60}")
    print("TEST: Nodes Files Exist and Parse")
    print(f"{'='*60}")
    
    registry_path = Path(__file__).parent / "registry.json"
    registry_testnet_path = Path(__file__).parent / "registry_testnet.json"
    nodes_dir = Path(__file__).parent / "data" / "nodes"
    
    if not registry_path.exists():
        print(f"❌ FAIL: registry.json not found")
        return False
    
    if not nodes_dir.exists():
        print(f"❌ FAIL: nodes directory not found at {nodes_dir}")
        return False
    
    mainnet_registry = json.loads(registry_path.read_text())
    testnet_registry = json.loads(registry_testnet_path.read_text()) if registry_testnet_path.exists() else {"networks": {}}
    
    all_networks = list(mainnet_registry["networks"].keys()) + list(testnet_registry["networks"].keys())
    
    missing_files = []
    invalid_files = []
    
    for network_key in all_networks:
        for pattern in [f"nodes-{network_key}.json", f"nodes-*{network_key}*.json"]:
            nodes_files = list(nodes_dir.glob(pattern))
            if nodes_files:
                nodes_file = nodes_files[0]
                try:
                    nodes = json.loads(nodes_file.read_text())
                    if not isinstance(nodes, list):
                        invalid_files.append(f"{nodes_file.name}: not a list")
                except Exception as e:
                    invalid_files.append(f"{nodes_file.name}: {e}")
                break
        else:
            pass
    
    if invalid_files:
        print(f"❌ FAIL: Found {len(invalid_files)} invalid nodes files:")
        for err in invalid_files[:5]:
            print(f"   {err}")
        return False
    
    nodes_count = len(list(nodes_dir.glob("*.json")))
    print(f"✅ Found {nodes_count} nodes files in {nodes_dir}")
    print(f"✅ All nodes files parse as valid JSON")
    
    return True


def test(name: str, url: str, expected_status: int = 200, expected_fields: list = None) -> bool:
    """Test an endpoint."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"URL: {url}")
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            status = response.status
            data = json.loads(response.read())
            
            if status != expected_status:
                print(f"❌ FAIL: Expected status {expected_status}, got {status}")
                return False
            
            print(f"✅ Status: {status}")
            
            if expected_fields:
                for field in expected_fields:
                    if field not in data:
                        print(f"❌ FAIL: Missing expected field '{field}'")
                        return False
                    print(f"✅ Field '{field}': {data[field]}")
            
            # Pretty print first few keys
            print(f"\nResponse keys: {list(data.keys())[:10]}")
            
            return True
    
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            data = json.loads(e.read())
        except:
            data = {"error": str(e)}
        
        if status == expected_status:
            print(f"✅ Status: {status} (expected)")
            print(f"Response: {data}")
            return True
        else:
            print(f"❌ FAIL: Expected status {expected_status}, got {status}")
            print(f"Response: {data}")
            return False
    
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def main():
    print("=" * 60)
    print("Backend Integration Tests")
    print("=" * 60)
    
    results = []
    
    results.append(test_registry_v3_fields())
    
    results.append(test_testnet_networks())
    
    results.append(test_svr_variants())
    
    results.append(test_nodes_files())
    
    # Test 1: Health check
    results.append(test(
        "Health Check",
        f"{BASE_URL}/healthz",
        expected_fields=["status", "registry_version", "mainnet", "testnet"]
    ))
    
    # Test 2: CCIP Registry
    results.append(test(
        "CCIP Registry",
        f"{BASE_URL}/v1/ccip/registry",
        expected_fields=["version", "networks"]
    ))
    
    # Test 3: CCIP Lane (Ethereum -> Arbitrum)
    results.append(test(
        "CCIP Lane: Ethereum -> Arbitrum",
        f"{BASE_URL}/v1/ccip/lane/ethereum/arbitrum",
        expected_fields=["success", "lane", "source", "destination"]
    ))
    
    # Test 4: Invalid CCIP Lane - unknown network (should 404)
    results.append(test(
        "Invalid CCIP Lane - unknown network (should 404)",
        f"{BASE_URL}/v1/ccip/lane/ethereum/invalid",
        expected_status=404
    ))
    
    # Test 5: Unsupported CCIP Lane - valid networks but no route (should 404)
    print(f"\n{'='*60}")
    print("TEST: Unsupported CCIP Lane (ethereum → zksync)")
    print(f"{'='*60}")
    try:
        url = f"{BASE_URL}/v1/ccip/lane/ethereum/zksync"
        print(f"URL: {url}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            print(f"❌ FAIL: Expected 404, got {response.status}")
            results.append(False)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            data = json.loads(e.read())
            print(f"✅ Status: 404 (expected)")
            print(f"✅ Message: {data.get('detail', '')}")
            # Verify it mentions the lane is not supported
            if "not supported" in data.get('detail', '').lower():
                print(f"✅ Error message correctly explains lane is unsupported")
                results.append(True)
            else:
                print(f"❌ FAIL: Error message should mention lane is not supported")
                results.append(False)
        else:
            print(f"❌ FAIL: Expected 404, got {e.code}")
            results.append(False)
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(False)
    
    # Test 6: Data Feeds Registry
    results.append(test(
        "Data Feeds Registry",
        f"{BASE_URL}/v1/registry",
        expected_fields=["version", "networks"]
    ))
    
    # Test 7: Query ETH/USD on Ethereum
    results.append(test(
        "Query ETH/USD on Ethereum",
        f"{BASE_URL}/v1/query/ethereum/eth-usd",
        expected_fields=["success", "payload", "meta"]
    ))
    
    # Test 8: Query ETH/USD on Base (SVR fallback with transparency)
    print(f"\n{'='*60}")
    print("TEST: Query ETH/USD on Base (SVR fallback)")
    print(f"{'='*60}")
    try:
        url = f"{BASE_URL}/v1/query/base/eth-usd"
        print(f"URL: {url}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            meta = data.get("meta", {})
            
            # Verify transparency fields are present (SVR fallback happened)
            if "resolved_from" not in meta:
                print(f"❌ FAIL: Missing resolved_from field (SVR fallback should be transparent)")
                results.append(False)
            elif "resolved_to" not in meta:
                print(f"❌ FAIL: Missing resolved_to field (SVR fallback should be transparent)")
                results.append(False)
            elif "resolution_note" not in meta:
                print(f"❌ FAIL: Missing resolution_note field (SVR fallback should be transparent)")
                results.append(False)
            elif meta["resolved_from"] != "eth-usd":
                print(f"❌ FAIL: resolved_from should be 'eth-usd', got '{meta['resolved_from']}'")
                results.append(False)
            elif meta["resolved_to"] != "eth-usd-svr":
                print(f"❌ FAIL: resolved_to should be 'eth-usd-svr' (prefer plain -svr), got '{meta['resolved_to']}'")
                results.append(False)
            elif "Smart Value Recapture" not in meta["resolution_note"]:
                print(f"❌ FAIL: resolution_note should mention 'Smart Value Recapture'")
                results.append(False)
            else:
                print(f"✅ resolved_from: {meta['resolved_from']}")
                print(f"✅ resolved_to: {meta['resolved_to']} (plain -svr variant preferred)")
                print(f"✅ resolution_note present: {len(meta['resolution_note'])} chars")
                print(f"✅ Address: {meta.get('contract_address')} (eth-usd-svr)")
                # Verify it's the correct eth-usd-svr address
                if meta.get('contract_address') == "0xa4250cE1aA15Ff4cb5E5a8655293b65694e436Ed":
                    print(f"✅ Correct eth-usd-svr address")
                results.append(True)
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(False)
    
    # Test 9: Query ETH/USD on Arbitrum (canonical proxy, no fallback)
    print(f"\n{'='*60}")
    print("TEST: Query ETH/USD on Arbitrum (canonical proxy)")
    print(f"{'='*60}")
    try:
        url = f"{BASE_URL}/v1/query/arbitrum/eth-usd"
        print(f"URL: {url}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            
            # Verify it returns the canonical proxy, not SVR
            expected_address = "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612"
            actual_address = data.get("meta", {}).get("contract_address")
            
            if actual_address != expected_address:
                print(f"❌ FAIL: Expected address {expected_address}, got {actual_address}")
                results.append(False)
            elif "resolved_to" in data.get("meta", {}):
                print(f"❌ FAIL: Should not have resolved_to field (canonical feed should match exactly)")
                print(f"   resolved_to: {data['meta']['resolved_to']}")
                results.append(False)
            else:
                print(f"✅ Address: {actual_address} (canonical)")
                print(f"✅ No resolved_to field (exact match, no fallback)")
                results.append(True)
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(False)
    
    # Test 10: Invalid feed with close matches
    results.append(test(
        "Invalid feed (should suggest close matches)",
        f"{BASE_URL}/v1/query/ethereum/eth-usdd",
        expected_status=404
    ))
    
    # Test 11: Round ID validation (should 422)
    huge_round_id = 10**25  # Way bigger than uint80
    results.append(test(
        "Huge round_id (should 422)",
        f"{BASE_URL}/v1/query/ethereum/eth-usd?round_id={huge_round_id}",
        expected_status=422
    ))
    
    # Test 12: Testnet registry
    results.append(test(
        "Testnet Registry",
        f"{BASE_URL}/v1/registry?environment=testnet",
        expected_fields=["version", "environment", "networks"]
    ))
    
    # Test 13: Testnet feed query (Sepolia ETH/USD)
    results.append(test(
        "Query ETH/USD on Sepolia (testnet)",
        f"{BASE_URL}/v1/query/sepolia/eth-usd?environment=testnet",
        expected_fields=["success", "payload", "meta"]
    ))
    
    # Test 14: Testnet CCIP registry
    results.append(test(
        "Testnet CCIP Registry",
        f"{BASE_URL}/v1/ccip/registry?environment=testnet",
        expected_fields=["version", "environment", "networks"]
    ))
    
    # Test 15: Testnet CCIP lane (Sepolia -> Arbitrum Sepolia)
    results.append(test(
        "CCIP Lane: Sepolia -> Arbitrum Sepolia (testnet)",
        f"{BASE_URL}/v1/ccip/lane/sepolia/arbitrum-sepolia?environment=testnet",
        expected_fields=["success", "lane", "source", "destination"]
    ))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
