"""
Refresh data validation checks
===============================
Production validation checks for the data refresh workflow.

These functions are called from the build scripts (build_registry.py,
build_ccip_registry.py, build_operators.py) to validate data integrity
and fail the build when critical thresholds are breached.
"""


def check_rdd_response_codes(responses: dict) -> None:
    """Check that all RDD and CCIP URLs returned 200.
    
    Args:
        responses: Dict mapping URL -> HTTP status code
        
    Raises:
        ValueError: If any URL returned non-200
    """
    failed = [url for url, code in responses.items() if code != 200]
    if failed:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: {len(failed)} URL(s) returned non-200:\n" +
            "\n".join(f"  {url}: HTTP {responses[url]}" for url in failed[:5])
        )


def check_transmitter_mapping_rate(network: str, mapped: int, total: int, threshold: float = 98.0) -> None:
    """Check that transmitter→operator mapping rate is above threshold.
    
    Args:
        network: Network name
        mapped: Number of mapped transmitters
        total: Total number of transmitters
        threshold: Minimum mapping percentage (default 98%)
        
    Raises:
        ValueError: If mapping rate is below threshold
    """
    if total == 0:
        return
    
    rate = (mapped / total) * 100
    if rate < threshold:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED for {network}: "
            f"Transmitter mapping rate {rate:.1f}% is below threshold {threshold}% "
            f"({mapped}/{total} transmitters mapped)"
        )


def check_feed_count_change(network: str, old_count: int, new_count: int, max_change_pct: float = 20.0) -> None:
    """Check that feed count hasn't changed by more than threshold.
    
    Args:
        network: Network name
        old_count: Previous feed count
        new_count: New feed count
        max_change_pct: Maximum allowed change percentage (default 20%)
        
    Raises:
        ValueError: If feed count change exceeds threshold
    """
    if old_count == 0:
        return
    
    change_pct = abs((new_count - old_count) / old_count) * 100
    if change_pct > max_change_pct:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED for {network}: "
            f"Feed count changed by {change_pct:.1f}% (from {old_count} to {new_count}), "
            f"exceeding {max_change_pct}% threshold"
        )


def check_rpc_failure_rate(failed: int, total: int, max_failure_pct: float = 30.0) -> None:
    """Check that RPC call failure rate is below threshold.
    
    Args:
        failed: Number of failed RPC calls
        total: Total number of RPC calls
        max_failure_pct: Maximum allowed failure percentage (default 30%)
        
    Raises:
        ValueError: If failure rate exceeds threshold
    """
    if total == 0:
        return
    
    failure_pct = (failed / total) * 100
    if failure_pct > max_failure_pct:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: "
            f"RPC failure rate {failure_pct:.1f}% exceeds {max_failure_pct}% "
            f"({failed}/{total} calls failed)"
        )


def check_hidden_operators(operators: list, hidden_patterns: list) -> None:
    """Check that no public operator matches hidden patterns.
    
    Args:
        operators: List of operator dicts with 'slug' and 'name' fields
        hidden_patterns: List of patterns to check against (case-insensitive)
        
    Raises:
        ValueError: If any public operator matches a hidden pattern
    """
    violations = []
    
    for op in operators:
        op_slug = op.get("slug", "").lower()
        op_name = op.get("name", "").lower()
        
        for pattern in hidden_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in op_slug or pattern_lower in op_name:
                violations.append(f"{op['slug']} (name: {op['name']}) matches hidden pattern '{pattern}'")
    
    if violations:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: {len(violations)} public operator(s) match hidden patterns:\n" +
            "\n".join(f"  {v}" for v in violations[:10])
        )


def check_no_hidden_transmitters(feed_operators: dict, hidden_addresses: set) -> None:
    """Check that feed_operators.json contains no hidden transmitter addresses.
    
    Args:
        feed_operators: Dict with per-network feed operator data
        hidden_addresses: Set of hidden transmitter addresses (lowercase)
        
    Raises:
        ValueError: If any feed contains a hidden transmitter address
    """
    violations = []
    
    for network_key, feeds in feed_operators.items():
        for feed_path, feed_data in feeds.items():
            transmitters = feed_data.get("transmitters", [])
            for addr in transmitters:
                if addr.lower() in hidden_addresses:
                    violations.append(f"{network_key}/{feed_path}: {addr}")
    
    if violations:
        raise ValueError(
            f"❌ REFRESH CHECK FAILED: {len(violations)} feed(s) contain hidden transmitter addresses:\n" +
            "\n".join(f"  {v}" for v in violations[:10])
        )
