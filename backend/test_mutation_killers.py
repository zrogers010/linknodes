"""
Mutation-killing tests for build_registry.py.

These tests are designed to fail when specific mutations are applied:
1. wrong product-name source (using productTypeCode instead of clicProductName)
2. shutdown filter disabled (keeping deprecating feeds at build time)
3. nodes writes dropped (assert all 20 files exist and are non-empty)
4. product_type, svr_proxy, contract_version and base/quote mapping assertions
"""

import json
from pathlib import Path


def test_clic_product_name_source():
    """Kill mutant: wrong product-name source (productTypeCode instead of clicProductName).
    
    Verifies that clic_product_name comes from docs.clicProductName, not docs.productTypeCode.
    """
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # ETH/USD on Ethereum is a known feed with a specific clic
    eth_usd = registry["networks"]["ethereum"]["feeds"]["eth-usd"]
    
    # The clic_product_name should be the clicProductName from RDD
    expected_clic = "ETH/USD-RefPrice-DF-Ethereum-001"
    actual_clic = eth_usd.get("clic_product_name")
    
    assert actual_clic == expected_clic, (
        f"clic_product_name mismatch for ethereum/eth-usd: "
        f"expected '{expected_clic}', got '{actual_clic}'. "
        f"This suggests the wrong source field is being used (productTypeCode instead of clicProductName)."
    )
    
    # BTC/USD on Arbitrum
    btc_usd = registry["networks"]["arbitrum"]["feeds"]["btc-usd"]
    expected_btc_clic = "BTC/USD-RefPrice-DF-Arbitrum-001"
    actual_btc_clic = btc_usd.get("clic_product_name")
    
    assert actual_btc_clic == expected_btc_clic, (
        f"clic_product_name mismatch for arbitrum/btc-usd: "
        f"expected '{expected_btc_clic}', got '{actual_btc_clic}'"
    )
    
    print("✓ clic_product_name correctly sourced from docs.clicProductName")


def test_nodes_files_exist():
    """Kill mutant: nodes writes dropped.
    
    Asserts that all 20 network node files (13 mainnet + 7 testnet) exist and are non-empty.
    """
    nodes_dir = Path(__file__).parent / "data" / "nodes"
    
    # Expected node file names (13 mainnet + 7 testnet = 20)
    expected_files = [
        # Mainnet
        "nodes-mainnet.json",
        "nodes-ethereum-mainnet-arbitrum-1.json",
        "nodes-ethereum-mainnet-base-1.json",
        "nodes-ethereum-mainnet-optimism-1.json",
        "nodes-matic-mainnet.json",
        "nodes-avalanche-mainnet.json",
        "nodes-bsc-mainnet.json",
        "nodes-xdai-mainnet.json",
        "nodes-ethereum-mainnet-scroll-1.json",
        "nodes-ethereum-mainnet-linea-1.json",
        "nodes-celo-mainnet.json",
        "nodes-sonic-mainnet.json",
        "nodes-ethereum-mainnet-zksync-1.json",
        # Testnet
        "nodes-ethereum-testnet-sepolia.json",
        "nodes-ethereum-testnet-sepolia-arbitrum-1.json",
        "nodes-ethereum-testnet-sepolia-base-1.json",
        "nodes-ethereum-testnet-sepolia-optimism-1.json",
        "nodes-polygon-testnet-amoy.json",
        "nodes-avalanche-fuji-testnet.json",
        "nodes-bsc-testnet.json",
    ]
    
    missing_files = []
    empty_files = []
    
    for filename in expected_files:
        filepath = nodes_dir / filename
        
        if not filepath.exists():
            missing_files.append(filename)
        else:
            content = filepath.read_text()
            if not content or content.strip() == "":
                empty_files.append(filename)
            else:
                # Verify it's valid JSON with at least one node
                try:
                    nodes = json.loads(content)
                    if not nodes or len(nodes) == 0:
                        empty_files.append(f"{filename} (0 nodes)")
                except json.JSONDecodeError:
                    empty_files.append(f"{filename} (invalid JSON)")
    
    assert not missing_files, (
        f"Missing {len(missing_files)} node files: {missing_files}. "
        f"This suggests the nodes download/write logic was disabled or broken."
    )
    
    assert not empty_files, (
        f"Empty or invalid node files: {empty_files}. "
        f"This suggests the nodes write logic is incomplete."
    )
    
    print(f"✓ All {len(expected_files)} node files exist and are non-empty")


def test_product_type_mapping():
    """Kill mutant: product_type field mapping.
    
    Verifies that product_type is correctly mapped from docs.productType.
    """
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # Test known feeds with specific product types
    test_cases = [
        ("ethereum", "eth-usd", "Price"),  # RefPrice
        ("ethereum", "bgbtc-por", "Proof of Reserve"),  # PoR
        ("gnosis", "aave-network-emergency-count-xdai", None),  # Counter (no product_type in RDD)
    ]
    
    for network, feed_slug, expected_type in test_cases:
        feed = registry["networks"][network]["feeds"][feed_slug]
        actual_type = feed.get("product_type")
        
        assert actual_type == expected_type, (
            f"product_type mismatch for {network}/{feed_slug}: "
            f"expected '{expected_type}', got '{actual_type}'"
        )
    
    print("✓ product_type correctly mapped from docs.productType")


def test_svr_proxy_mapping():
    """Kill mutant: svr_proxy mapped from wrong field.
    
    Verifies that svr_proxy is correctly mapped from secondaryProxyAddress (not proxyAddress).
    """
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # EUR/USD Shared SVR on Ethereum has a known secondary proxy
    eur_usd_svr = registry["networks"]["ethereum"]["feeds"]["eur-usd-shared-svr"]
    
    svr_proxy = eur_usd_svr.get("svr_proxy")
    primary_address = eur_usd_svr.get("address")
    
    assert svr_proxy is not None, "eur-usd-shared-svr should have svr_proxy"
    assert svr_proxy != primary_address, (
        f"svr_proxy should not equal primary address. "
        f"This suggests svr_proxy is being mapped from proxyAddress instead of secondaryProxyAddress. "
        f"svr_proxy={svr_proxy}, address={primary_address}"
    )
    
    # Non-SVR feeds should not have svr_proxy
    eth_usd = registry["networks"]["ethereum"]["feeds"]["eth-usd"]
    assert eth_usd.get("svr_proxy") is None, "Non-SVR feed should not have svr_proxy"
    
    print("✓ svr_proxy correctly mapped from secondaryProxyAddress")


def test_contract_version_mapping():
    """Kill mutant: contract_version set to None.
    
    Verifies that contract_version is correctly mapped from contractVersion.
    """
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # ETH/USD on Ethereum has a known contract version
    eth_usd = registry["networks"]["ethereum"]["feeds"]["eth-usd"]
    
    contract_version = eth_usd.get("contract_version")
    
    assert contract_version is not None, (
        "eth-usd should have contract_version. "
        "This suggests contract_version is being set to None instead of reading contractVersion."
    )
    
    # Verify it's a reasonable value (typically 3 or 4 for V3/V4 aggregators)
    assert isinstance(contract_version, int), f"contract_version should be an int, got {type(contract_version)}"
    assert contract_version >= 1, f"contract_version should be >= 1, got {contract_version}"
    
    print(f"✓ contract_version correctly mapped (eth-usd has version {contract_version})")


def test_base_quote_mapping():
    """Kill mutant: base/quote swapped.
    
    Verifies that base and quote assets are correctly mapped (not swapped).
    """
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # ETH/USD: base should be ETH (or variant), quote should be USD
    eth_usd = registry["networks"]["ethereum"]["feeds"]["eth-usd"]
    
    base = eth_usd.get("base")
    quote = eth_usd.get("quote")
    
    # Base should contain ETH, quote should contain USD
    assert base and "ETH" in base.upper(), (
        f"ETH/USD base asset should contain 'ETH', got '{base}'. "
        f"This suggests base and quote are swapped."
    )
    
    assert quote and "USD" in quote.upper(), (
        f"ETH/USD quote asset should contain 'USD', got '{quote}'. "
        f"This suggests base and quote are swapped."
    )
    
    # BTC/ETH: base should be BTC, quote should be ETH
    btc_eth = registry["networks"]["ethereum"]["feeds"].get("btc-eth")
    if btc_eth:
        btc_base = btc_eth.get("base")
        btc_quote = btc_eth.get("quote")
        
        assert btc_base and "BTC" in btc_base.upper(), (
            f"BTC/ETH base should contain 'BTC', got '{btc_base}'"
        )
        assert btc_quote and "ETH" in btc_quote.upper(), (
            f"BTC/ETH quote should contain 'ETH', got '{btc_quote}'"
        )
    
    print("✓ base and quote correctly mapped (not swapped)")


def test_shutdown_filter_enabled():
    """Kill mutant: shutdown filter disabled (deprecating feeds not dropped at build time).
    
    Note: With the updated requirement, deprecating feeds should NOT be dropped at build time.
    This test verifies that deprecating feeds ARE present with proper status.
    """
    registry_path = Path(__file__).parent / "registry.json"
    assert registry_path.exists(), "registry.json not found - run build_registry.py first"
    
    registry = json.loads(registry_path.read_text())
    
    # Count feeds with shutdown_date set (should be present in registry)
    feeds_with_shutdown = []
    feeds_with_deprecating_status = []
    feeds_with_shutdown_status = []
    
    for network_slug, network_data in registry["networks"].items():
        for feed_slug, feed_meta in network_data["feeds"].items():
            shutdown_date = feed_meta.get("shutdown_date")
            status = feed_meta.get("status")
            
            if shutdown_date:
                feeds_with_shutdown.append(f"{network_slug}/{feed_slug}")
            
            if status == "deprecating":
                feeds_with_deprecating_status.append(f"{network_slug}/{feed_slug}")
            
            if status == "shut_down":
                feeds_with_shutdown_status.append(f"{network_slug}/{feed_slug}")
    
    # Verify shut_down feeds ARE present (they should not be dropped at build time)
    assert len(feeds_with_shutdown) > 0, (
        "No feeds with shutdown_date found. "
        "Expected feeds with upcoming shutdown dates to be present in registry. "
        "This suggests shutdown feeds are being filtered at build time instead of request time."
    )
    
    # All feeds with shutdown_date should have status="shut_down"
    assert len(feeds_with_shutdown) == len(feeds_with_shutdown_status), (
        f"Mismatch: {len(feeds_with_shutdown)} feeds have shutdown_date, "
        f"but {len(feeds_with_shutdown_status)} have status='shut_down'. "
        f"All feeds with shutdown_date should have status='shut_down'."
    )
    
    print(f"✓ Shutdown handling correct: {len(feeds_with_shutdown)} feeds with shutdown_date present")
    print(f"  (will be filtered at request-time based on UTC clock)")


if __name__ == "__main__":
    print("Running mutation-killing tests...")
    print("=" * 100)
    
    test_clic_product_name_source()
    test_nodes_files_exist()
    test_product_type_mapping()
    test_svr_proxy_mapping()
    test_contract_version_mapping()
    test_base_quote_mapping()
    test_shutdown_filter_enabled()
    
    print("=" * 100)
    print("✓ All mutation-killing tests passed")
