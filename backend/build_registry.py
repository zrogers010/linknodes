"""
Registry generator
==================
Pulls Chainlink's published reference-data directory (the same source that
powers docs.chain.link) for every supported mainnet chain and compiles it into
the static `registry.json` the engine serves from memory.

Run whenever you want to refresh the catalog:

    .venv/bin/python build_registry.py
"""

import json
import os
import shutil
import time
from pathlib import Path

import httpx

RDD_BASE = "https://reference-data-directory.vercel.app"

# chain key -> (RDD file, label, chain_id, explorer, rpc urls)
MAINNET_CHAINS: dict[str, tuple[str, str, int, str, list[str]]] = {
    "ethereum": (
        "feeds-mainnet",
        "Ethereum",
        1,
        "https://etherscan.io",
        ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com", "https://rpc.ankr.com/eth"],
    ),
    "arbitrum": (
        "feeds-ethereum-mainnet-arbitrum-1",
        "Arbitrum One",
        42161,
        "https://arbiscan.io",
        ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"],
    ),
    "base": (
        "feeds-ethereum-mainnet-base-1",
        "Base",
        8453,
        "https://basescan.org",
        ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],
    ),
    "optimism": (
        "feeds-ethereum-mainnet-optimism-1",
        "OP Mainnet",
        10,
        "https://optimistic.etherscan.io",
        ["https://mainnet.optimism.io", "https://optimism-rpc.publicnode.com"],
    ),
    "polygon": (
        "feeds-matic-mainnet",
        "Polygon PoS",
        137,
        "https://polygonscan.com",
        ["https://polygon-bor-rpc.publicnode.com", "https://polygon-rpc.com"],
    ),
    "avalanche": (
        "feeds-avalanche-mainnet",
        "Avalanche C-Chain",
        43114,
        "https://snowtrace.io",
        ["https://api.avax.network/ext/bc/C/rpc", "https://avalanche-c-chain-rpc.publicnode.com"],
    ),
    "bnb": (
        "feeds-bsc-mainnet",
        "BNB Smart Chain",
        56,
        "https://bscscan.com",
        ["https://bsc-dataseed.bnbchain.org", "https://bsc-rpc.publicnode.com"],
    ),
    "gnosis": (
        "feeds-xdai-mainnet",
        "Gnosis",
        100,
        "https://gnosisscan.io",
        ["https://rpc.gnosischain.com", "https://gnosis-rpc.publicnode.com"],
    ),
    "scroll": (
        "feeds-ethereum-mainnet-scroll-1",
        "Scroll",
        534352,
        "https://scrollscan.com",
        ["https://rpc.scroll.io", "https://scroll-rpc.publicnode.com"],
    ),
    "linea": (
        "feeds-ethereum-mainnet-linea-1",
        "Linea",
        59144,
        "https://lineascan.build",
        ["https://rpc.linea.build", "https://linea-rpc.publicnode.com"],
    ),
    "celo": (
        "feeds-celo-mainnet",
        "Celo",
        42220,
        "https://celoscan.io",
        ["https://forno.celo.org", "https://celo-rpc.publicnode.com"],
    ),
    "sonic": (
        "feeds-sonic-mainnet",
        "Sonic",
        146,
        "https://sonicscan.org",
        ["https://rpc.soniclabs.com", "https://sonic-rpc.publicnode.com"],
    ),
    "zksync": (
        "feeds-ethereum-mainnet-zksync-1",
        "ZKsync Era",
        324,
        "https://era.zksync.network",
        ["https://mainnet.era.zksync.io"],
    ),
}

TESTNET_CHAINS: dict[str, tuple[str, str, int, str, list[str]]] = {
    "sepolia": (
        "feeds-ethereum-testnet-sepolia",
        "Ethereum Sepolia",
        11155111,
        "https://sepolia.etherscan.io",
        ["https://ethereum-sepolia-rpc.publicnode.com", "https://rpc.sepolia.org"],
    ),
    "arbitrum-sepolia": (
        "feeds-ethereum-testnet-sepolia-arbitrum-1",
        "Arbitrum Sepolia",
        421614,
        "https://sepolia.arbiscan.io",
        ["https://sepolia-rollup.arbitrum.io/rpc", "https://arbitrum-sepolia-rpc.publicnode.com"],
    ),
    "base-sepolia": (
        "feeds-ethereum-testnet-sepolia-base-1",
        "Base Sepolia",
        84532,
        "https://sepolia.basescan.org",
        ["https://sepolia.base.org", "https://base-sepolia-rpc.publicnode.com"],
    ),
    "optimism-sepolia": (
        "feeds-ethereum-testnet-sepolia-optimism-1",
        "OP Sepolia",
        11155420,
        "https://sepolia-optimism.etherscan.io",
        ["https://sepolia.optimism.io", "https://optimism-sepolia-rpc.publicnode.com"],
    ),
    "polygon-amoy": (
        "feeds-polygon-testnet-amoy",
        "Polygon Amoy",
        80002,
        "https://amoy.polygonscan.com",
        ["https://rpc-amoy.polygon.technology", "https://polygon-amoy-bor-rpc.publicnode.com"],
    ),
    "avalanche-fuji": (
        "feeds-avalanche-fuji-testnet",
        "Avalanche Fuji",
        43113,
        "https://testnet.snowtrace.io",
        ["https://api.avax-test.network/ext/bc/C/rpc", "https://avalanche-fuji-c-chain-rpc.publicnode.com"],
    ),
    "bnb-testnet": (
        "feeds-bsc-testnet",
        "BNB Testnet",
        97,
        "https://testnet.bscscan.com",
        ["https://bsc-testnet-rpc.publicnode.com", "https://data-seed-prebsc-1-s1.bnbchain.org:8545"],
    ),
}

SKIP_CATEGORIES = {"hidden"}


def include(feed: dict) -> bool:
    """Determine if a feed should be included in the registry.
    
    Keep all feeds with a proxyAddress except hidden ones.
    Deprecating and dated feeds are kept; visibility is decided at request time.
    """
    docs = feed.get("docs") or {}
    return bool(
        feed.get("proxyAddress")
        and feed.get("path")
        and not docs.get("hidden")
        and (feed.get("feedCategory") or "") not in SKIP_CATEGORIES
    )


def parse_shutdown_date(shutdown_text: str | None) -> str | None:
    """Parse RDD shutdown date text to ISO YYYY-MM-DD format.
    
    Handles formats like:
    - "October 18th, 2026" -> "2026-10-18"
    - "February 2026" -> "2026-02-28" (last day of month)
    - None -> None
    - Unparseable -> raises ValueError (fail closed, not fail open)
    """
    if not shutdown_text:
        return None
    
    import re
    from datetime import datetime
    from calendar import monthrange
    
    # Try "Month DDth, YYYY" format
    match = re.match(r'(\w+)\s+(\d+)(?:st|nd|rd|th)?,\s+(\d{4})', shutdown_text)
    if match:
        month_name, day, year = match.groups()
        try:
            dt = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # Try "Month YYYY" format (use last day of month)
    match = re.match(r'(\w+)\s+(\d{4})', shutdown_text)
    if match:
        month_name, year = match.groups()
        try:
            dt = datetime.strptime(f"{month_name} {year}", "%B %Y")
            last_day = monthrange(dt.year, dt.month)[1]
            return f"{year}-{dt.month:02d}-{last_day:02d}"
        except ValueError:
            pass
    
    # Unparseable date - fail the build (fail closed)
    raise ValueError(f"Unable to parse shutdown date: '{shutdown_text}'")



def compute_feed_status(category: str | None, shutdown_date_iso: str | None, utc_now: str | None = None) -> str:
    """Compute feed status based on category and shutdown date vs UTC today.
    
    Args:
        category: Feed category from RDD
        shutdown_date_iso: Shutdown date in ISO YYYY-MM-DD format (must be valid)
        utc_now: Current UTC date for testing (format: YYYY-MM-DD). If None, uses today.
    
    Returns:
        - "shut_down" if shutdown_date is in the past OR malformed
        - "deprecating" if shutdown_date is today/future OR category is deprecating
        - "active" otherwise
    """
    if shutdown_date_iso:
        from datetime import datetime, timezone
        import re
        
        if utc_now is None:
            utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Validate ISO YYYY-MM-DD format
        # Malformed dates are treated as hidden (fail closed)
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', shutdown_date_iso):
            # Malformed date -> treat as immediately shut down (hidden)
            return "shut_down"
        
        # Compare dates as strings (YYYY-MM-DD format sorts correctly)
        if shutdown_date_iso < utc_now:
            return "shut_down"
        else:
            # Today or future => deprecating
            return "deprecating"
    
    if category == "deprecating":
        return "deprecating"
    
    return "active"


def compact(feed: dict) -> dict:
    docs = feed.get("docs") or {}
    shutdown_date_raw = docs.get("shutdownDate")
    shutdown_date_iso = parse_shutdown_date(shutdown_date_raw)
    category = feed.get("feedCategory") or "unranked"
    
    return {
        "name": feed["name"],
        "path": feed["path"],
        "address": feed["proxyAddress"],
        "aggregator": feed.get("contractAddress"),
        "contract_version": feed.get("contractVersion"),
        "svr_proxy": feed.get("secondaryProxyAddress"),
        "svr_label": feed.get("svrDisplayLabel"),
        "decimals": feed.get("decimals"),
        "heartbeat": feed.get("heartbeat"),
        "deviation_threshold_pct": feed.get("threshold"),
        "category": category,
        "feed_type": (feed.get("feedType") or docs.get("assetClass") or "Other").capitalize(),
        "product_type": docs.get("productType"),
        "base": docs.get("baseAsset"),
        "quote": docs.get("quoteAsset"),
        "asset_name": feed.get("assetName") or docs.get("baseAsset") or "",
        "market_hours": docs.get("marketHours"),
        "issuer": docs.get("issuer"),
        "por_auditor": docs.get("porAuditor"),
        "por_source": docs.get("porSource"),
        "clic_product_name": docs.get("clicProductName"),
        "shutdown_date": shutdown_date_iso,
        "status": compute_feed_status(category, shutdown_date_iso),
        "base_path": None,
    }


def verify_rpc_chain_id(rpc_url: str, expected_chain_id: int) -> bool:
    """Verify RPC returns the expected chain ID."""
    try:
        resp = httpx.post(
            rpc_url,
            json={"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
            timeout=5,
        )
        result = resp.json().get("result")
        if result:
            actual_chain_id = int(result, 16)
            return actual_chain_id == expected_chain_id
    except Exception:
        pass
    return False


def validate_source_data(feeds: list, nodes: list, network_label: str) -> None:
    """Validate source data shape and fail loudly if required keys are missing in ≥1% of entries."""
    if not feeds and not nodes:
        return
    
    if feeds:
        required_feed_keys = ["proxyAddress", "contractAddress", "heartbeat", "decimals", "path"]
        total_feeds = len(feeds)
        
        for key in required_feed_keys:
            missing_count = sum(1 for feed in feeds if key not in feed or feed.get(key) is None)
            missing_pct = (missing_count / total_feeds) * 100 if total_feeds > 0 else 0
            
            if missing_pct >= 1.0:
                raise ValueError(
                    f"❌ VALIDATION FAILED for {network_label}: "
                    f"Required key '{key}' is missing in {missing_count}/{total_feeds} live feeds ({missing_pct:.1f}%). "
                    f"This indicates a source shape change that requires code updates."
                )
    
    if nodes:
        required_node_keys = ["id", "name"]
        address_keys = ["nodeAddress", "oracleAddress", "payeeAddress", "forwarderAddress"]
        total_nodes = len(nodes)
        
        for key in required_node_keys:
            missing_count = sum(1 for node in nodes if key not in node or node.get(key) is None)
            missing_pct = (missing_count / total_nodes) * 100 if total_nodes > 0 else 0
            
            if missing_pct >= 1.0:
                raise ValueError(
                    f"❌ VALIDATION FAILED for {network_label} nodes: "
                    f"Required key '{key}' is missing in {missing_count}/{total_nodes} nodes ({missing_pct:.1f}%)."
                )
        
        has_address_count = sum(
            1 for node in nodes
            if any(node.get(addr_key) for addr_key in address_keys)
        )
        missing_pct = ((total_nodes - has_address_count) / total_nodes) * 100 if total_nodes > 0 else 0
        
        if missing_pct >= 1.0:
            raise ValueError(
                f"❌ VALIDATION FAILED for {network_label} nodes: "
                f"{total_nodes - has_address_count}/{total_nodes} nodes ({missing_pct:.1f}%) "
                f"are missing all address fields ({', '.join(address_keys)})."
            )


def write_nodes(mainnet_staged_dir: Path, testnet_staged_dir: Path, dest_dir: Path) -> None:
    """Write staged nodes files to destination directory atomically.
    
    Design:
    - data/nodes stays a real tracked git directory (not a symlink)
    - Stage ALL files (mainnet + testnet) into temp dir on same filesystem
    - Validate all staged files
    - Only after all validation passes, atomically replace each file with os.replace()
    - Delete stale files that are no longer in the set
    - If any staging step fails, data/nodes is untouched
    
    Args:
        mainnet_staged_dir: Path to directory containing staged mainnet .json files
        testnet_staged_dir: Path to directory containing staged testnet .json files  
        dest_dir: Path to destination nodes directory (data/nodes)
    """
    import tempfile
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Stage all files in temp directory on same filesystem (backend/data/)
    # This ensures os.replace() will be atomic
    staging_parent = dest_dir.parent  # backend/data/
    with tempfile.TemporaryDirectory(dir=staging_parent, prefix=".nodes_staging_") as tmpdir:
        staging_dir = Path(tmpdir)
        
        # Copy all mainnet files to staging
        for staged_file in mainnet_staged_dir.glob("*.json"):
            dest = staging_dir / staged_file.name
            shutil.copy2(staged_file, dest)
        
        # Copy all testnet files to staging
        for staged_file in testnet_staged_dir.glob("*.json"):
            dest = staging_dir / staged_file.name
            shutil.copy2(staged_file, dest)
        
        # All files staged successfully - now atomically replace each one
        staged_files = set()
        for staged_file in staging_dir.glob("*.json"):
            target = dest_dir / staged_file.name
            # os.replace() is atomic on the same filesystem
            os.replace(staged_file, target)
            staged_files.add(staged_file.name)
        
        # Clean up stale files that are no longer in the set
        for existing_file in dest_dir.glob("nodes-*.json"):
            if existing_file.name not in staged_files:
                existing_file.unlink()


def link_svr_variants(feeds: dict[str, dict]) -> None:
    """Link SVR variant feeds to their base feeds by updating base_path in-place.
    
    Args:
        feeds: Dictionary of feed slug -> feed data (modified in-place)
    """
    for slug, compacted in feeds.items():
        if compacted.get("svr_label"):
            clic_name = compacted.get("clic_product_name")
            svr_name = compacted.get("name", "").lower()
            svr_base = compacted.get("base")
            svr_quote = compacted.get("quote")
            
            matching_candidates = []
            
            for candidate_slug, candidate in feeds.items():
                if candidate_slug == slug:
                    continue
                if candidate.get("svr_label"):
                    continue
                
                candidate_clic = candidate.get("clic_product_name")
                candidate_name = candidate.get("name", "").lower()
                
                # Try clic-based matching first
                if clic_name and candidate_clic and clic_name.lower() == candidate_clic.lower():
                    # Additional criteria: compatible market hours, method, and product type
                    svr_hours = compacted.get("market_hours")
                    candidate_hours = candidate.get("market_hours")
                    svr_product = compacted.get("product_type")
                    candidate_product = candidate.get("product_type")
                    
                    # Check for methodology mismatch in feed names
                    # (Calculated vs Ondo API are different methodologies)
                    svr_has_calculated = "calculated" in svr_name
                    svr_has_ondo_api = "ondo api" in svr_name
                    cand_has_calculated = "calculated" in candidate_name
                    cand_has_ondo_api = "ondo api" in candidate_name
                    
                    methodology_mismatch = (
                        (svr_has_calculated and cand_has_ondo_api) or
                        (svr_has_ondo_api and cand_has_calculated)
                    )
                    
                    # Consider compatible if:
                    # - Market hours match (or at least one is missing/empty)
                    # - Product type matches (or at least one is missing)
                    # - No methodology mismatch
                    hours_compatible = (
                        not svr_hours or not candidate_hours or 
                        svr_hours == candidate_hours
                    )
                    product_compatible = (
                        not svr_product or not candidate_product or
                        svr_product == candidate_product
                    )
                    
                    if hours_compatible and product_compatible and not methodology_mismatch:
                        matching_candidates.append(candidate_slug)
                
                # Fallback: match on name + base/quote when clic differs
                elif not clic_name or not candidate_clic or clic_name.lower() != candidate_clic.lower():
                    # Extract base feed name by removing methodology/svr suffixes
                    def normalize_feed_name(name):
                        n = name.lower()
                        # Remove common suffixes
                        for suffix in [" (calculated)", " (ondo api)", " shared svr", " svr", " - svr"]:
                            n = n.replace(suffix, "")
                        return n.strip()
                    
                    svr_normalized = normalize_feed_name(svr_name)
                    cand_normalized = normalize_feed_name(candidate_name)
                    
                    # Match on normalized name + base/quote
                    if (svr_normalized == cand_normalized and
                        svr_base and svr_quote and
                        candidate.get("base") == svr_base and
                        candidate.get("quote") == svr_quote):
                        matching_candidates.append(candidate_slug)
            
            # Only link if exactly one candidate matches
            if len(matching_candidates) == 1:
                compacted["base_path"] = matching_candidates[0]
            elif len(matching_candidates) > 1:
                # Ambiguous match - leave unlinked
                print(f"    ⚠ Ambiguous SVR match for {slug}: {len(matching_candidates)} candidates")


def build_registry(chains: dict, environment: str, http_client=None, output_dir=None) -> dict:
    """Build registry for a specific environment (mainnet or testnet)."""
    from refresh_checks import check_rdd_response_codes, check_feed_count_change
    
    # Determine output directory
    backend_dir = output_dir or Path(__file__).parent
    existing_path = backend_dir / ("registry.json" if environment == "mainnet" else "registry_testnet.json")
    
    # Read existing registry to check if content changes
    existing_data = None
    existing_generated_at = None
    
    if existing_path.exists():
        try:
            with open(existing_path) as f:
                existing_data = json.load(f)
                existing_generated_at = existing_data.get("generated_at")
        except Exception:
            pass
    
    # Start with existing generated_at (will update if content changed)
    registry: dict = {
        "version": "3.0.0",
        "environment": environment,
        "source": "chainlink-reference-data-directory",
        "generated_at": existing_generated_at or int(time.time()),
        "networks": {},
    }
    total = 0
    
    # Track all HTTP responses for validation
    http_responses = {}
    
    # Stage downloaded data in temp directory before committing
    import tempfile
    import shutil
    temp_dir = Path(tempfile.mkdtemp(prefix="registry_build_"))

    try:
        # Use provided client or create default one
        if http_client is None:
            client_ctx = httpx.Client(timeout=30)
            client = client_ctx.__enter__()
            should_close = True
        else:
            client = http_client
            should_close = False
        
        try:
            for key, (rdd_file, label, chain_id, explorer, rpcs) in chains.items():
                print(f"{label:<25} ", end="", flush=True)
                
                if verify_rpc_chain_id(rpcs[0], chain_id):
                    print(f"✓ chain_id={chain_id:<8} ", end="", flush=True)
                else:
                    print(f"⚠ chain_id unverified ", end="", flush=True)
                
                try:
                    resp = client.get(f"{RDD_BASE}/{rdd_file}.json")
                    http_responses[f"{RDD_BASE}/{rdd_file}.json"] = resp.status_code
                    resp.raise_for_status()
                    raw = resp.json()
                    
                    nodes_file = rdd_file.replace("feeds-", "nodes-")
                    nodes_resp = client.get(f"{RDD_BASE}/{nodes_file}.json")
                    http_responses[f"{RDD_BASE}/{nodes_file}.json"] = nodes_resp.status_code
                    nodes_resp.raise_for_status()
                    nodes = nodes_resp.json()
                    
                    # Stage in temp directory
                    temp_nodes_path = temp_dir / f"{nodes_file}.json"
                    temp_nodes_path.write_text(json.dumps(nodes, indent=1))
                    
                    live_feeds = [feed for feed in raw if include(feed)]
                    validate_source_data(live_feeds, nodes, label)

                    feeds: dict[str, dict] = {}
                    compacted_feeds = []
                    
                    for feed in live_feeds:
                        slug = feed["path"]
                        compacted = compact(feed)
                        compacted_feeds.append((slug, compacted, feed))
                        feeds[slug] = compacted
                    
                    # SVR matching - link variants to base feeds
                    link_svr_variants(feeds)

                    registry["networks"][key] = {
                        "label": label,
                        "chain_id": chain_id,
                        "explorer": explorer,
                        "rpc_urls": rpcs,
                        "feed_count": len(feeds),
                        "feeds": dict(sorted(feeds.items())),
                    }
                    total += len(feeds)
                    print(f"{len(feeds):>4} feeds")
                except Exception as e:
                    print(f"ERROR: {e}")
                    raise
        finally:
            if should_close:
                client_ctx.__exit__(None, None, None)
        
        # Check if content changed - update generated_at if it did
        if existing_data is not None and existing_generated_at is not None:
            # Compare new registry (with old generated_at) to existing
            # If byte-identical, keep old generated_at; otherwise update it
            new_with_old_time = json.dumps(registry, indent=1)
            existing_serialized = json.dumps(existing_data, indent=1)
            
            if new_with_old_time != existing_serialized:
                # Content changed - update generated_at
                registry["generated_at"] = int(time.time())
        
        # All validations passed - return registry and staged nodes directory
        # (Nodes will be written atomically in main() after all builds succeed)
        
        # Run refresh checks
        try:
            check_rdd_response_codes(http_responses)
        except ValueError as e:
            print(f"\n{e}\n")
            raise
        
        return registry, total, temp_dir
    
    except Exception:
        # Clean up temp directory on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def main(http_client=None, output_dir=None) -> None:
    """Build and write registries.
    
    Args:
        http_client: Optional httpx.Client for testing
        output_dir: Optional output directory for testing (defaults to backend/)
    """
    print("=" * 70)
    print("Building Data Feeds Registries")
    print("=" * 70)
    
    mainnet_temp_dir = None
    testnet_temp_dir = None
    
    try:
        # Build both registries first (validate everything before writing)
        print("\nMAINNET:")
        print("-" * 70)
        mainnet_registry, mainnet_total, mainnet_temp_dir = build_registry(MAINNET_CHAINS, "mainnet", http_client, output_dir)
        print(f"✓ Built mainnet: {mainnet_total} feeds across {len(MAINNET_CHAINS)} chains")
        
        print("\nTESTNET:")
        print("-" * 70)
        testnet_registry, testnet_total, testnet_temp_dir = build_registry(TESTNET_CHAINS, "testnet", http_client, output_dir)
        print(f"✓ Built testnet: {testnet_total} feeds across {len(TESTNET_CHAINS)} chains")
        
        # All builds succeeded - write outputs atomically
        print("\nWriting outputs...")
        
        import tempfile
        backend_dir = output_dir or Path(__file__).parent
        
        # Write registries to temp files first
        with tempfile.NamedTemporaryFile(mode='w', dir=backend_dir, delete=False, suffix='.tmp') as tmp:
            tmp.write(json.dumps(mainnet_registry, indent=1))
            tmp_mainnet = tmp.name
        
        with tempfile.NamedTemporaryFile(mode='w', dir=backend_dir, delete=False, suffix='.tmp') as tmp:
            tmp.write(json.dumps(testnet_registry, indent=1))
            tmp_testnet = tmp.name
        
        # Atomic replace for registries
        mainnet_path = backend_dir / "registry.json"
        testnet_path = backend_dir / "registry_testnet.json"
        
        os.replace(tmp_mainnet, mainnet_path)
        os.replace(tmp_testnet, testnet_path)
        
        # Write nodes files atomically (combined mainnet + testnet in single swap)
        nodes_dir = backend_dir / "data" / "nodes"
        write_nodes(mainnet_temp_dir, testnet_temp_dir, nodes_dir)
        
        print(f"✓ Wrote {mainnet_path.name}: {mainnet_total} feeds across {len(MAINNET_CHAINS)} chains "
              f"({mainnet_path.stat().st_size / 1024:.0f} KB)")
        print(f"✓ Wrote {testnet_path.name}: {testnet_total} feeds across {len(TESTNET_CHAINS)} chains "
              f"({testnet_path.stat().st_size / 1024:.0f} KB)")
        
        print("\n" + "=" * 70)
        print(f"Total: {mainnet_total + testnet_total} feeds across {len(MAINNET_CHAINS) + len(TESTNET_CHAINS)} chains")
        print("=" * 70)
        
    finally:
        # Clean up temp directories
        if mainnet_temp_dir:
            shutil.rmtree(mainnet_temp_dir, ignore_errors=True)
        if testnet_temp_dir:
            shutil.rmtree(testnet_temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
