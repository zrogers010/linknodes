#!/usr/bin/env python3
"""
CCIP Data Verification
======================
Compare our CCIP registry values against Chainlink's official API.
"""

import json
import urllib.request


def fetch_official():
    """Fetch official CCIP data."""
    req = urllib.request.Request(
        'https://docs.chain.link/api/ccip/v1/chains?environment=mainnet',
        headers={'User-Agent': 'LinkNodes-Verification/1.0'}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())


def main():
    # Load our registry
    with open('ccip_registry.json') as f:
        our_data = json.load(f)
    
    # Fetch official
    print("Fetching official CCIP data from Chainlink API...")
    official_data = fetch_official()
    
    print("\n" + "=" * 80)
    print("CCIP Data Verification: Our Registry vs Official API")
    print("=" * 80)
    
    # Map our keys to chain IDs
    chain_map = {
        'ethereum': '1',
        'arbitrum': '42161',
        'avalanche': '43114',
        'base': '8453',
        'bnb': '56',
        'optimism': '10',
        'polygon': '137',
        'wemix': '1111',
        'zksync': '324'
    }
    
    for our_key, chain_id in chain_map.items():
        our_net = our_data['networks'][our_key]
        official_net = official_data['data']['evm'].get(chain_id)
        
        if not official_net:
            print(f"\n⚠️  {our_key}: Not in official API")
            continue
        
        print(f"\n{our_net['label']} (Chain ID: {chain_id})")
        print("-" * 80)
        
        # Compare chain selector
        match = "✅" if our_net['chain_selector'] == official_net['selector'] else "❌"
        print(f"{match} Chain Selector:")
        print(f"    Ours:     {our_net['chain_selector']}")
        print(f"    Official: {official_net['selector']}")
        
        # Compare router
        match = "✅" if our_net['router'].lower() == official_net['router'].lower() else "❌"
        print(f"{match} Router:")
        print(f"    Ours:     {our_net['router']}")
        print(f"    Official: {official_net['router']}")
        
        # Compare RMN
        match = "✅" if our_net['rmn_proxy'].lower() == official_net['rmn'].lower() else "❌"
        print(f"{match} RMN Proxy:")
        print(f"    Ours:     {our_net['rmn_proxy']}")
        print(f"    Official: {official_net['rmn']}")
    
    print("\n" + "=" * 80)
    print("Verification complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
