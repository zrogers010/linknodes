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
    
    # Test 4: Invalid CCIP Lane (should 404)
    results.append(test(
        "Invalid CCIP Lane (should 404)",
        f"{BASE_URL}/v1/ccip/lane/ethereum/invalid",
        expected_status=404
    ))
    
    # Test 5: Data Feeds Registry
    results.append(test(
        "Data Feeds Registry",
        f"{BASE_URL}/v1/registry",
        expected_fields=["version", "networks"]
    ))
    
    # Test 6: Query ETH/USD on Ethereum
    results.append(test(
        "Query ETH/USD on Ethereum",
        f"{BASE_URL}/v1/query/ethereum/eth-usd",
        expected_fields=["success", "payload", "meta"]
    ))
    
    # Test 7: Query ETH/USD on Base (canonical name resolution)
    results.append(test(
        "Query ETH/USD on Base (canonical resolution)",
        f"{BASE_URL}/v1/query/base/eth-usd",
        expected_fields=["success", "payload", "meta"]
    ))
    
    # Test 8: Invalid feed with close matches
    results.append(test(
        "Invalid feed (should suggest close matches)",
        f"{BASE_URL}/v1/query/ethereum/eth-usdd",
        expected_status=404
    ))
    
    # Test 9: Round ID validation (should 422)
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
