import { isSessionBasedHours } from './marketHours'
import type { FeedMeta, Registry, SandboxState } from './types'

export type Lang = 'solidity' | 'javascript' | 'python' | 'curl'

const STALE_BUFFER = 900

function heartbeatSeconds(feed: Pick<FeedMeta, 'heartbeat'>): number {
  return feed.heartbeat && feed.heartbeat > 0 ? feed.heartbeat : 3600
}

function l2Flags(network: string): { hasSequencer: boolean; showSequencerNote: boolean } {
  const l2Chains = ['arbitrum', 'base', 'optimism', 'scroll', 'linea', 'zksync']
  const chainKey = network.toLowerCase().split(' ')[0]
  const isTestnet =
    network.toLowerCase().includes('sepolia') ||
    network.toLowerCase().includes('amoy') ||
    network.toLowerCase().includes('fuji') ||
    network.toLowerCase().includes('testnet')
  const hasSequencer = l2Chains.some((l2) => chainKey.includes(l2))
  return { hasSequencer, showSequencerNote: hasSequencer && isTestnet }
}

function sequencerBlock(network: string): string {
  const { hasSequencer, showSequencerNote } = l2Flags(network)
  if (!hasSequencer) return ''
  return `
    // L2 Sequencer uptime check (only for L2 chains like Arbitrum, Base, OP, etc.)
    // Sequencer feed: 0 = up, 1 = down. Revert if down or grace period not elapsed.${showSequencerNote ? `
    // NOTE: ${network} may not have a published sequencer uptime feed.` : ''}
    // Find sequencer feed addresses: https://docs.chain.link/data-feeds/l2-sequencer-feeds
    AggregatorV3Interface internal constant SEQUENCER_FEED =
        AggregatorV3Interface(0xFdB631F5EE196F0ed6FAa767959853A9F217697D); // Example: Arbitrum mainnet
    uint256 private constant GRACE_PERIOD_TIME = 3600;

    function _checkSequencer() internal view {
        (, int256 answer, uint256 startedAt,,) = SEQUENCER_FEED.latestRoundData();
        require(answer == 0, "Sequencer down");
        require(block.timestamp - startedAt > GRACE_PERIOD_TIME, "Grace period not over");
    }
`
}

function solidityCrypto(address: string, name: string, network: string, heartbeat: number): string {
  const { hasSequencer } = l2Flags(network)
  const sequencerCheck = sequencerBlock(network)

  return `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from
    "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

/// ${name} Chainlink feed on ${network}
/// Safe integration: per-feed heartbeat, answer validation, decimals handling
contract PriceConsumer {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(${address});
    /// Heartbeat from this feed's reference-data-directory metadata (seconds).
    uint256 public constant HEARTBEAT = ${heartbeat};
    uint256 public constant STALE_BUFFER = ${STALE_BUFFER};
    ${sequencerCheck}
    /// Returns latest price with safety checks
    function latestPrice() external view returns (int256 price, uint8 decimals) {${hasSequencer ? '\n        _checkSequencer();' : ''}
        (uint80 roundId, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        
        // Safety checks
        require(answer > 0, "Invalid price");
        require(updatedAt > 0, "Round not complete");
        require(roundId > 0, "Invalid round");
        
        // Staleness: this feed's heartbeat + 900s buffer (not a hardcoded 3600).
        require(block.timestamp - updatedAt <= HEARTBEAT + STALE_BUFFER, "Stale price");
        
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

function solidityEquities(address: string, name: string, network: string, heartbeat: number): string {
  const { hasSequencer } = l2Flags(network)
  const sequencerCheck = sequencerBlock(network)

  return `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from
    "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

/// ${name} — 24/5 / NYSE-hours consumer on ${network}
/// Docs:
///   https://docs.chain.link/data-streams/market-hours
///   https://docs.chain.link/data-streams/rwa-streams/24-5-us-equities-user-guide
///   https://docs.chain.link/data-feeds/24-7-extended-hours-data-feeds
/// Streams marketStatus (use the report field, never timestamps):
///   0 Unknown, 1 Pre, 2 Regular, 3 Post, 4 Overnight, 5 Closed
/// On-chain Data Feeds do not expose marketStatus. Pass marketClosed from
/// an off-chain NYSE calendar (or from a Streams marketStatus == 5).
/// When the cash market is closed, 24/5 feeds pause — that gap is not stale.
contract EquitiesHoursConsumer {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(${address});
    /// Per-feed heartbeat from the reference-data directory (seconds).
    uint256 public constant HEARTBEAT = ${heartbeat};
    uint256 public constant STALE_BUFFER = ${STALE_BUFFER};
    /// Reject zero/negative answers and moves larger than 20% vs last accepted.
    uint256 public constant MAX_JUMP_BPS = 2_000;

    int256 public lastGoodPrice;
    ${sequencerCheck}
    event PriceAccepted(int256 price, uint256 updatedAt, bool restricted);

    /// @param marketClosed true when the cash session is Closed (or marketStatus == 5).
    /// Restricted mode returns the last published tick without a staleness revert.
    function readPrice(bool marketClosed)
        external
        returns (int256 price, uint8 decimals, bool restricted)
    {${hasSequencer ? '\n        _checkSequencer();' : ''}
        (uint80 roundId, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        require(answer > 0, "Invalid price"); // reject zero / negative
        require(updatedAt > 0, "Round not complete");
        require(roundId > 0, "Invalid round");

        if (lastGoodPrice > 0) {
            uint256 basis = uint256(lastGoodPrice);
            uint256 latest = uint256(answer);
            uint256 diff = latest > basis ? latest - basis : basis - latest;
            require(diff * 10_000 <= basis * MAX_JUMP_BPS, "Implausible jump");
        }

        if (marketClosed) {
            lastGoodPrice = answer;
            emit PriceAccepted(answer, updatedAt, true);
            return (answer, FEED.decimals(), true);
        }

        require(block.timestamp - updatedAt <= HEARTBEAT + STALE_BUFFER, "Stale price");
        lastGoodPrice = answer;
        emit PriceAccepted(answer, updatedAt, false);
        return (answer, FEED.decimals(), false);
    }
}`
}

function solidity(feed: FeedMeta, network: string): string {
  const heartbeat = heartbeatSeconds(feed)
  if (isSessionBasedHours(feed.market_hours)) {
    return solidityEquities(feed.address, feed.name, network, heartbeat)
  }
  return solidityCrypto(feed.address, feed.name, network, heartbeat)
}

function javascript(feed: FeedMeta, rpc: string): string {
  const heartbeat = heartbeatSeconds(feed)
  const hoursAware = isSessionBasedHours(feed.market_hours)
  const hoursNote = hoursAware
    ? `
// 24/5 / NYSE hours: do not treat the weekend/holiday gap as stale.
// Docs: https://docs.chain.link/data-streams/rwa-streams/24-5-us-equities-user-guide
// marketStatus (Streams only): 0 Unknown, 1 Pre, 2 Regular, 3 Post, 4 Overnight, 5 Closed
// Use marketStatus from the report when you have Streams access; never timestamps.
const marketClosed = false; // set from an NYSE calendar or marketStatus === 5
if (marketClosed) {
  console.log(\`Market closed, last update \${new Date(Number(updatedAt) * 1000).toISOString()}\`);
} else if (age > HEARTBEAT + ${STALE_BUFFER}) {
  console.warn(\`Price is stale (\${age}s old; heartbeat \${HEARTBEAT}s)\`);
}`
    : `
if (age > HEARTBEAT + ${STALE_BUFFER}) {
  console.warn(\`Price is stale (\${age}s old; heartbeat \${HEARTBEAT}s)\`);
}`

  return `// Save as feed-query.mjs (note .mjs extension for ES modules)
// npm install ethers
import { ethers } from "ethers";

const FEED = "${feed.address}"; // ${feed.name}
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

// Per-feed heartbeat from the catalog (not a hardcoded 3600 / 86400).
const HEARTBEAT = ${heartbeat};
const age = Math.floor(Date.now() / 1000) - Number(updatedAt);${hoursNote}

// Historical round (roundIds encode the proxy phase in the upper 16 bits):
const [, prevAnswer] = await feed.getRoundData(roundId - 1n);
console.log("previous round:", ethers.formatUnits(prevAnswer, decimals));`
}

function python(feed: FeedMeta, rpc: string): string {
  const heartbeat = heartbeatSeconds(feed)
  return `# pip install web3
from web3 import Web3

FEED = "${feed.address}"  # ${feed.name}
ABI = [
    {"name": "latestRoundData", "inputs": [], "stateMutability": "view", "type": "function",
     "outputs": [{"type": "uint80"}, {"type": "int256"}, {"type": "uint256"},
                 {"type": "uint256"}, {"type": "uint80"}]},
    {"name": "getRoundData", "stateMutability": "view", "type": "function",
     "inputs": [{"type": "uint80"}],
     "outputs": [{"type": "uint80"}, {"type": "int256"}, {"type": "uint256"},
                 {"type": "uint80"}]},
    {"name": "decimals", "inputs": [], "stateMutability": "view", "type": "function",
     "outputs": [{"type": "uint8"}]},
]

w3 = Web3(Web3.HTTPProvider("${rpc}"))
feed = w3.eth.contract(address=FEED, abi=ABI)

decimals = feed.functions.decimals().call()
round_id, answer, _, updated_at, _ = feed.functions.latestRoundData().call()

print(f"price: {answer / 10**decimals}")
print(f"updated_at (unix): {updated_at}")

# Per-feed heartbeat from the catalog
HEARTBEAT = ${heartbeat}
age = __import__("time").time() - updated_at
if age > HEARTBEAT + ${STALE_BUFFER}:
    print(f"stale: {int(age)}s old (heartbeat {HEARTBEAT}s)")

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
  if (lang === 'solidity') return solidity(feed, net.label)
  if (lang === 'javascript') return javascript(feed, rpc)
  if (lang === 'curl') return curl(feed.address, feed.name, rpc, feed.decimals)
  return python(feed, rpc)
}
