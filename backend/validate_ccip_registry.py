"""
CCIP Registry Validation
========================
Validates ccip_registry.json for correctness:
- EIP-55 checksum addresses (using Web3.py if available)
- Chain selector format
- Required fields present
- Consistent cross-references

Run: python validate_ccip_registry.py
"""

import json
import sys
from pathlib import Path


def validate_address_format(address: str) -> tuple[bool, str]:
    """Basic address format validation."""
    if not address.startswith('0x'):
        return False, "Missing 0x prefix"
    if len(address) != 42:
        return False, f"Wrong length: {len(address)} (expected 42)"
    
    # Check if it's valid hex
    try:
        int(address[2:], 16)
    except ValueError:
        return False, "Invalid hex"
    
    # Try EIP-55 validation with Web3 if available
    try:
        from web3 import Web3
        if address != Web3.to_checksum_address(address):
            return False, "EIP-55 checksum failed"
    except ImportError:
        # Web3 not available, just warn
        pass
    
    return True, "OK"


def validate_chain_selector(selector: str) -> tuple[bool, str]:
    """Validate chain selector is a numeric string."""
    try:
        val = int(selector)
        if val <= 0:
            return False, "Must be positive"
        if val > 2**64 - 1:
            return False, "Exceeds uint64 max"
        return True, "OK"
    except ValueError:
        return False, "Not a valid integer"


def validate_registry(registry_path: Path):
    """Validate a single CCIP registry file."""
    if not registry_path.exists():
        print(f"Error: {registry_path} not found")
        return False
    
    registry = json.loads(registry_path.read_text())
    
    print("=" * 60)
    print(f"CCIP Registry Validation: {registry_path.name}")
    print("=" * 60)
    print(f"Version: {registry.get('version')}")
    print(f"Source: {registry.get('source')}")
    print(f"Networks: {len(registry.get('networks', {}))}")
    print()
    
    errors = []
    warnings = []
    
    for net_key, net_data in registry.get('networks', {}).items():
        print(f"Validating {net_data.get('label', net_key)}...")
        
        # Check required fields
        required = ['label', 'chain_id', 'chain_selector', 'router', 'rpc_urls']
        for field in required:
            if field not in net_data:
                errors.append(f"{net_key}: missing required field '{field}'")
        
        # Validate chain selector
        if 'chain_selector' in net_data:
            valid, msg = validate_chain_selector(net_data['chain_selector'])
            if not valid:
                errors.append(f"{net_key}: invalid chain_selector: {msg}")
        
        # Validate router address
        if 'router' in net_data:
            valid, msg = validate_address_format(net_data['router'])
            if not valid:
                errors.append(f"{net_key}: invalid router address: {msg}")
            elif msg != "OK":
                warnings.append(f"{net_key}: router {msg}")
        
        # Validate RMN proxy address if present
        if 'rmn_proxy' in net_data:
            valid, msg = validate_address_format(net_data['rmn_proxy'])
            if not valid:
                errors.append(f"{net_key}: invalid rmn_proxy address: {msg}")
            elif msg != "OK":
                warnings.append(f"{net_key}: rmn_proxy {msg}")
        
        # Validate supports list
        if 'supports' in net_data:
            for dest in net_data['supports']:
                if dest not in registry['networks']:
                    errors.append(f"{net_key}: supports references unknown network '{dest}'")
    
    print()
    print("=" * 60)
    
    if errors:
        print(f"❌ {len(errors)} error(s) found:")
        for err in errors:
            print(f"  - {err}")
        print()
    
    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):")
        for warn in warnings:
            print(f"  - {warn}")
        print()
    
    if not errors and not warnings:
        print("✅ All validations passed!")
    elif not errors:
        print("✅ No errors (warnings only)")
    
    print("=" * 60)
    
    return len(errors) == 0


def main():
    base_dir = Path(__file__).parent
    registry_files = ["ccip_registry.json", "ccip_registry_testnet.json"]
    
    all_passed = True
    for filename in registry_files:
        registry_path = base_dir / filename
        if registry_path.exists():
            passed = validate_registry(registry_path)
            all_passed = all_passed and passed
            print()
        else:
            print(f"⚠️  {filename} not found, skipping")
            print()
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
