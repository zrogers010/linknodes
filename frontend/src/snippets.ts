import type { Registry, SandboxState } from './types'

export type Lang = 'solidity' | 'javascript' | 'python' | 'curl'

function solidity(address: string, name: string, network: string): string {
  return `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from
    "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

/// ${name} Chainlink feed on ${network}
contract PriceConsumer {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(${address});

    function latestPrice() external view returns (int256 answer, uint256 updatedAt) {
        (, answer, , updatedAt, ) = FEED.latestRoundData();
    }

    /// Historical lookup -- pass a roundId from a previous latestRoundData().
    function priceAtRound(uint80 roundId) external view returns (int256 answer) {
        (, answer, , , ) = FEED.getRoundData(roundId);
    }

    function decimals() external view returns (uint8) {
        return FEED.decimals();
    }
}`
}

function javascript(address: string, name: string, rpc: string): string {
  return `// npm install ethers
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
