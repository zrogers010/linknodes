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

# Test without external dependencies
import urllib.request
import urllib.error


BASE_URL = "http://127.0.0.1:8100"


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
    
    # Test 1: Health check
    results.append(test(
        "Health Check",
        f"{BASE_URL}/healthz",
        expected_fields=["status", "registry_version", "ccip_networks"]
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
    
    # Test 8: Query ETH/USD on Base (canonical proxy, no fallback)
    print(f"\n{'='*60}")
    print("TEST: Query ETH/USD on Base (canonical proxy)")
    print(f"{'='*60}")
    try:
        url = f"{BASE_URL}/v1/query/base/eth-usd"
        print(f"URL: {url}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            
            # Verify it returns the canonical proxy, not SVR
            expected_address = "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70"
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
