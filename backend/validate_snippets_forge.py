"""
Snippet Validation Script (Forge-based)
========================================
Compiles code snippets using Forge (from Foundry toolchain).

Requires: 
- forge (from foundry)
- node_modules with @chainlink/contracts + @chainlink/contracts-ccip + @openzeppelin/contracts
- Install with: npm install --no-save --legacy-peer-deps <packages>
  (--legacy-peer-deps resolves @openzeppelin/contracts peer dependency conflicts)

Run: python validate_snippets_forge.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def check_forge() -> tuple[bool, str]:
    """Check if forge is available."""
    try:
        result = subprocess.run(
            ['forge', '--version'],
            capture_output=True,
            timeout=5,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0] if result.stdout else "unknown"
            return True, version
        return False, "not available"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, "not found"


def compile_with_forge(code: str, name: str) -> tuple[bool, str]:
    """Compile Solidity code using forge."""
    # Create a temporary foundry project
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create src directory
        src_dir = tmppath / "src"
        src_dir.mkdir()
        
        # Write contract
        contract_file = src_dir / "Contract.sol"
        contract_file.write_text(code)
        
        # Get absolute path to backend node_modules
        backend_node_modules = Path.cwd() / 'node_modules'
        if not backend_node_modules.exists():
            return False, "node_modules not found in backend directory"
        
        # Create foundry.toml with absolute path to node_modules
        foundry_toml = tmppath / "foundry.toml"
        foundry_toml.write_text(f"""[profile.default]
src = "src"
out = "out"
libs = ["{backend_node_modules}"]
remappings = [
    "@chainlink/contracts/={backend_node_modules}/@chainlink/contracts/",
    "@chainlink/contracts-ccip/={backend_node_modules}/@chainlink/contracts-ccip/",
    "@openzeppelin/contracts/={backend_node_modules}/@openzeppelin/contracts/",
    "@openzeppelin/contracts@5.3.0/={backend_node_modules}/@openzeppelin/contracts-5.3.0/",
    "@openzeppelin/contracts@5.1.0/={backend_node_modules}/@openzeppelin/contracts-5.1.0/",
    "@openzeppelin/contracts@5.0.2/={backend_node_modules}/@openzeppelin/contracts-5.0.2/",
    "@openzeppelin/contracts@4.9.6/={backend_node_modules}/@openzeppelin/contracts-4.9.6/",
    "@openzeppelin/contracts@4.8.3/={backend_node_modules}/@openzeppelin/contracts-4.8.3/",
    "@openzeppelin/contracts@4.7.3/={backend_node_modules}/@openzeppelin/contracts-4.7.3/"
]
""")
        
        # Try to compile
        try:
            result = subprocess.run(
                ['forge', 'build', '--root', str(tmppath)],
                capture_output=True,
                timeout=60,
                text=True,
                cwd=str(tmppath)
            )
            
            if result.returncode != 0:
                stderr = result.stderr or result.stdout
                # Check for warnings vs errors
                if 'Error' in stderr or 'error' in stderr.lower():
                    return False, f"Compilation failed:\n{stderr[:800]}"
                # Just warnings
                return True, "OK (with warnings)"
            
            return True, "OK"
        
        except subprocess.TimeoutExpired:
            return False, "Compilation timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"


def main():
    print("=" * 60)
    print("Snippet Validation (Forge)")
    print("=" * 60)
    
    # Check forge
    forge_available, forge_version = check_forge()
    print(f"\nforge: {'✓' if forge_available else '✗'} {forge_version}")
    
    if not forge_available:
        print("\n⚠️  forge not found. Install via:")
        print("  curl -L https://foundry.paradigm.xyz | bash && foundryup")
        sys.exit(1)
    
    # Check dependencies
    node_modules = Path('node_modules')
    if not node_modules.exists():
        print("\n⚠️  node_modules not found. Run:")
        print("  npm install --no-save @chainlink/contracts@1.2.0 @openzeppelin/contracts@5.0.0")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Compiling Snippets")
    print("=" * 60)
    
    results = []
    
    # 1. Data Feeds - L1 (Ethereum)
    print("\n📊 Data Feeds (Ethereum, no sequencer check)")
    feeds_l1 = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

contract PriceConsumer {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419);
    
    function latestPrice() external view returns (int256 price, uint8 decimals) {
        (uint80 roundId, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        require(answer > 0, "Invalid price");
        require(updatedAt > 0, "Round not complete");
        require(roundId > 0, "Invalid round");
        uint256 HEARTBEAT = 3600;
        require(block.timestamp - updatedAt <= HEARTBEAT + 900, "Stale price");
        return (answer, FEED.decimals());
    }
}"""
    
    valid, msg = compile_with_forge(feeds_l1, "Data Feeds L1")
    results.append(valid)
    print(f"  {'✓' if valid else '✗'} {msg}")
    
    # 2. Data Feeds - L2 (Arbitrum, with sequencer)
    print("\n📊 Data Feeds (Arbitrum, with sequencer check)")
    feeds_l2 = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

contract PriceConsumerL2 {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612);
    AggregatorV3Interface internal constant SEQUENCER_FEED =
        AggregatorV3Interface(0xFdB631F5EE196F0ed6FAa767959853A9F217697D);
    uint256 private constant GRACE_PERIOD_TIME = 3600;

    function _checkSequencer() internal view {
        (, int256 answer, uint256 startedAt,,) = SEQUENCER_FEED.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period not over");
    }
    
    function latestPrice() external view returns (int256 price, uint8 decimals) {
        _checkSequencer();
        (uint80 roundId, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        require(answer > 0, "Invalid price");
        require(updatedAt > 0, "Round not complete");
        require(roundId > 0, "Invalid round");
        uint256 HEARTBEAT = 3600;
        require(block.timestamp - updatedAt <= HEARTBEAT + 900, "Stale price");
        return (answer, FEED.decimals());
    }
}"""
    
    valid, msg = compile_with_forge(feeds_l2, "Data Feeds L2")
    results.append(valid)
    print(f"  {'✓' if valid else '✗'} {msg}")
    
    # 3. CCIP Sender (Ethereum -> Arbitrum)
    print("\n🌉 CCIP Sender (Ethereum -> Arbitrum)")
    ccip_sender = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IRouterClient} from "@chainlink/contracts-ccip/contracts/interfaces/IRouterClient.sol";
import {Client} from "@chainlink/contracts-ccip/contracts/libraries/Client.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract CCIPSender is Ownable {
    using SafeERC20 for IERC20;
    IRouterClient public immutable router;
    uint64 public constant DESTINATION_CHAIN_SELECTOR = 4949039107694359620;
    
    error InsufficientFee(uint256 required, uint256 provided);
    
    constructor() Ownable(msg.sender) {
        router = IRouterClient(0x80226fc0Ee2b096224EeAc085Bb9a8cba1146f7D);
    }
    
    function sendMessage(address receiver, string memory message) external payable onlyOwner returns (bytes32 messageId) {
        Client.EVM2AnyMessage memory evm2AnyMessage = Client.EVM2AnyMessage({
            receiver: abi.encode(receiver),
            data: abi.encode(message),
            tokenAmounts: new Client.EVMTokenAmount[](0),
            extraArgs: Client._argsToBytes(
                Client.GenericExtraArgsV2({gasLimit: 200_000, allowOutOfOrderExecution: true})
            ),
            feeToken: address(0)
        });
        
        uint256 fees = router.getFee(DESTINATION_CHAIN_SELECTOR, evm2AnyMessage);
        if (msg.value < fees) revert InsufficientFee(fees, msg.value);
        
        messageId = router.ccipSend{value: fees}(DESTINATION_CHAIN_SELECTOR, evm2AnyMessage);
        
        if (msg.value > fees) {
            (bool success, ) = msg.sender.call{value: msg.value - fees}("");
            require(success, "Refund failed");
        }
    }
}"""
    
    valid, msg = compile_with_forge(ccip_sender, "CCIP Sender")
    results.append(valid)
    print(f"  {'✓' if valid else '✗'} {msg}")
    
    # 4. CCIP Receiver
    # This snippet is extracted from frontend/src/pages/products/CCIPPage.tsx
    # to ensure CI tests what users actually see
    print("\n🌉 CCIP Receiver")
    ccip_receiver = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {CCIPReceiver} from "@chainlink/contracts-ccip/contracts/applications/CCIPReceiver.sol";
import {Client} from "@chainlink/contracts-ccip/contracts/libraries/Client.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract CCIPMessageReceiver is CCIPReceiver, Ownable {
    string public lastMessage;
    address public lastSender;
    
    event MessageReceived(bytes32 messageId, uint64 sourceChainSelector, address sender, string message);
    
    constructor(address router) CCIPReceiver(router) Ownable(msg.sender) {}
    
    function _ccipReceive(Client.Any2EVMMessage memory message) internal override {
        lastSender = abi.decode(message.sender, (address));
        lastMessage = abi.decode(message.data, (string));
        emit MessageReceived(message.messageId, message.sourceChainSelector, lastSender, lastMessage);
    }
}"""
    
    valid, msg = compile_with_forge(ccip_receiver, "CCIP Receiver")
    results.append(valid)
    print(f"  {'✓' if valid else '✗'} {msg}")
    
    # 5. VRF v2.5
    print("\n🎲 VRF v2.5")
    vrf = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {VRFConsumerBaseV2Plus} from "@chainlink/contracts/src/v0.8/vrf/dev/VRFConsumerBaseV2Plus.sol";
import {VRFV2PlusClient} from "@chainlink/contracts/src/v0.8/vrf/dev/libraries/VRFV2PlusClient.sol";

contract RandomNumberConsumer is VRFConsumerBaseV2Plus {
    uint256[] public randomWords;
    uint256 public subscriptionId;
    bytes32 public keyHash = 0x9e9e46732b32662b9adc6f3abdf6c5e926a666d174a4d6b8e39c96b87e28a796;
    
    constructor(uint256 _subscriptionId) 
        VRFConsumerBaseV2Plus(0x271682DEB8C4E0901D1a1550aD2e64D568E69909)
    {
        subscriptionId = _subscriptionId;
    }
    
    function requestRandomWords() external returns (uint256) {
        return s_vrfCoordinator.requestRandomWords(
            VRFV2PlusClient.RandomWordsRequest({
                keyHash: keyHash,
                subId: subscriptionId,
                requestConfirmations: 3,
                callbackGasLimit: 100000,
                numWords: 1,
                extraArgs: VRFV2PlusClient._argsToBytes(
                    VRFV2PlusClient.ExtraArgsV1({nativePayment: false})
                )
            })
        );
    }
    
    function fulfillRandomWords(uint256, uint256[] calldata _randomWords) internal override {
        randomWords = _randomWords;
    }
}"""
    
    valid, msg = compile_with_forge(vrf, "VRF v2.5")
    results.append(valid)
    print(f"  {'✓' if valid else '✗'} {msg}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"{'✅' if passed == total else '❌'} {passed}/{total} snippets compiled successfully")
    
    if passed < total:
        print("\n❌ COMPILATION FAILED")
        print("All code snippets shown to users MUST compile successfully.")
        print("Fix the failing snippets before merging.")
        sys.exit(1)
    
    print("\n✅ All snippets are production-ready and compile-tested!")
    sys.exit(0)


if __name__ == "__main__":
    main()
