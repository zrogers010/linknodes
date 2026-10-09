import type { Registry, SandboxState } from './types'

export type Lang = 'solidity' | 'javascript' | 'python' | 'curl'

function solidity(address: string, name: string, network: string): string {
  // Determine if this chain has an L2 sequencer uptime feed
  // Testnet sequencer feeds may not be available, so we'll show a conditional check
  const l2Chains = ['arbitrum', 'base', 'optimism', 'scroll', 'linea', 'zksync']
  const chainKey = network.toLowerCase().split(' ')[0]  // Extract first word
  const isTestnet = network.toLowerCase().includes('sepolia') || network.toLowerCase().includes('amoy') || network.toLowerCase().includes('fuji') || network.toLowerCase().includes('testnet')
  const hasSequencer = l2Chains.some(l2 => chainKey.includes(l2))
  const showSequencerNote = hasSequencer && isTestnet
  
  const sequencerCheck = hasSequencer ? `
    // L2 Sequencer uptime check (only for L2 chains like Arbitrum, Base, OP, etc.)
    // Sequencer feed: 0 = up, 1 = down. Revert if down or grace period not elapsed.${showSequencerNote ? `
    // NOTE: ${network} may not have a published sequencer uptime feed.` : ''}
    // Find sequencer feed addresses: https://docs.chain.link/data-feeds/l2-sequencer-feeds
    AggregatorV3Interface internal constant SEQUENCER_FEED =
        AggregatorV3Interface(0xFdB631F5EE196F0ed6FAa767959853A9F217697D); // Example: Arbitrum mainnet

    function _checkSequencer() internal view {
        (, int256 answer, uint256 startedAt,,) = SEQUENCER_FEED.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period not over");
    }
` : ''

  return `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from
    "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

/// ${name} Chainlink feed on ${network}
/// Safe integration: staleness check, answer validation, decimals handling
contract PriceConsumer {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(${address});
    ${sequencerCheck}
    /// Returns latest price with safety checks
    function latestPrice() external view returns (int256 price, uint8 decimals) {${hasSequencer ? '\n        _checkSequencer();' : ''}
        (uint80 roundId, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        
        // Safety checks
        require(answer > 0, "Invalid price");
        require(updatedAt > 0, "Round not complete");
        require(roundId > 0, "Invalid round");
        
        // Staleness check: revert if price older than heartbeat + buffer
        // Adjust HEARTBEAT based on feed (3600 for most crypto, 86400 for equities)
        uint256 HEARTBEAT = 3600;
        require(block.timestamp - updatedAt <= HEARTBEAT + 900, "Stale price");
        
        return (answer, FEED.decimals());
    }

    /// Historical lookup -- pass a roundId from a previous latestRoundData()
    function priceAtRound(uint80 roundId) external view returns (int256 answer) {
        (, answer,, uint256 updatedAt,) = FEED.getRoundData(roundId);
        require(answer > 0, "Invalid price");
        require(updatedAt > 0, "Round not complete");
    }

    /// Get human-readable price (scaled by decimals)
    function getScaledPrice() external view returns (uint256) {
        (int256 price, uint8 decimals) = this.latestPrice();
        // Example: convert to 18 decimals for DeFi integrations
        return uint256(price) * 10**(18 - decimals);
    }
}`
}

function javascript(address: string, name: string, rpc: string): string {
  return `// Save as feed-query.mjs (note .mjs extension for ES modules)
// npm install ethers
import { ethers } from "ethers";

const FEED = "${address}"; // ${name}
const ABI = [
  "function latestRoundData() view returns (uint80, int256, uint256, uint256, uint80)",
  "function getRoundData(uint80) view returns (uint80, int256, uint256, uint256, uint80)",
  "function decimals() view returns (uint8)",
];

const provider = new ethers.JsonRpcProvider("${rpc}");
const feed = new ethers.Contract(FEED, ABI, provider);

const [decimals, [roundId, answer, , updatedAt]] = await Promise.all([
  feed.decimals(),
  feed.latestRoundData(),
]);

console.log("price:", ethers.formatUnits(answer, decimals));
console.log("updated:", new Date(Number(updatedAt) * 1000).toISOString());

// Staleness check
const HEARTBEAT = 3600; // seconds (adjust based on feed)
const age = Math.floor(Date.now() / 1000) - Number(updatedAt);
if (age > HEARTBEAT + 900) {
  console.warn(\`⚠️  Price is stale (\${age}s old)\`);
}

// Historical round (roundIds encode the proxy phase in the upper 16 bits):
const [, prevAnswer] = await feed.getRoundData(roundId - 1n);
console.log("previous round:", ethers.formatUnits(prevAnswer, decimals));`
}

function python(address: string, name: string, rpc: string): string {
  return `# pip install web3
from web3 import Web3

FEED = "${address}"  # ${name}
ABI = [
    {"name": "latestRoundData", "inputs": [], "stateMutability": "view", "type": "function",
     "outputs": [{"type": "uint80"}, {"type": "int256"}, {"type": "uint256"},
                 {"type": "uint256"}, {"type": "uint80"}]},
    {"name": "getRoundData", "stateMutability": "view", "type": "function",
     "inputs": [{"type": "uint80"}],
     "outputs": [{"type": "uint80"}, {"type": "int256"}, {"type": "uint256"},
                 {"type": "uint256"}, {"type": "uint80"}]},
    {"name": "decimals", "inputs": [], "stateMutability": "view", "type": "function",
     "outputs": [{"type": "uint8"}]},
]

w3 = Web3(Web3.HTTPProvider("${rpc}"))
feed = w3.eth.contract(address=FEED, abi=ABI)

decimals = feed.functions.decimals().call()
round_id, answer, _, updated_at, _ = feed.functions.latestRoundData().call()

print(f"price: {answer / 10**decimals}")
print(f"updated_at (unix): {updated_at}")

# Historical round (round IDs encode the proxy phase in the upper 16 bits):
_, prev_answer, _, _, _ = feed.functions.getRoundData(round_id - 1).call()
print(f"previous round: {prev_answer / 10**decimals}")`
}

function curl(address: string, name: string, rpc: string, decimals: number | null): string {
  return `# Raw JSON-RPC eth_call -- no libraries, no keys, works anywhere.
# ${name}
# 0xfeaf968c = first 4 bytes of keccak256("latestRoundData()")

curl -s ${rpc} \\
  -H 'Content-Type: application/json' \\
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "eth_call",
    "params": [
      {"to": "${address}", "data": "0xfeaf968c"},
      "latest"
    ]
  }'

# The result is five ABI-encoded 32-byte words:
#   roundId | answer | startedAt | updatedAt | answeredInRound
# price = int(answer_hex, 16) / 10**${decimals ?? '<decimals>'}
#
# Decode inline with python:
#   ... | python3 -c 'import sys,json; r=json.load(sys.stdin)["result"][2:]; \\
#       print(int(r[64:128],16)/10**${decimals ?? 8})'`
}

export function buildSnippet(registry: Registry, state: SandboxState, lang: Lang): string {
  const net = registry.networks[state.network]
  const feed = net?.feeds[state.feed]
  if (!net || !feed) {
    return `// '${state.feed}' is not published on ${net?.label ?? state.network}.\n// Pick a feed from the catalog on the left -- coverage differs per chain.`
  }
  const rpc = net.rpc_urls[0]
  if (lang === 'solidity') return solidity(feed.address, feed.name, net.label)
  if (lang === 'javascript') return javascript(feed.address, feed.name, rpc)
  if (lang === 'curl') return curl(feed.address, feed.name, rpc, feed.decimals)
  return python(feed.address, feed.name, rpc)
}
