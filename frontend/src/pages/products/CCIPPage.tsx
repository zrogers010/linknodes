import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ProductLayout } from '../../components/ProductLayout'
import { apiUrl } from '../../config'
import { CopyButton } from '../../components/CopyButton'
import { SEO } from '../../components/SEO'

interface CCIPNetwork {
  network: string
  label: string
  chain_id: number
  chain_selector: string
  router: string
  rmn_proxy?: string
  native_fee_token?: string
  explorer: string
  rpc_urls: string[]
}

interface CCIPRegistry {
  version: string
  data_source_url?: string
  networks: Record<string, {
    label: string
    chain_id: number
    chain_selector: string
    router: string
    rmn_proxy?: string
    native_fee_token?: string
    explorer: string
    rpc_urls: string[]
    supports: string[]
  }>
}

interface LaneData {
  success: boolean
  lane: string
  source: CCIPNetwork
  destination: CCIPNetwork
}

export function CCIPPage() {
  const { source, dest } = useParams<{ source?: string; dest?: string }>()
  const navigate = useNavigate()
  const [registry, setRegistry] = useState<CCIPRegistry | null>(null)
  const [sourceChain, setSourceChain] = useState('')
  const [destChain, setDestChain] = useState('')
  const [laneData, setLaneData] = useState<LaneData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(apiUrl('/v1/ccip/registry'))
      .then((r) => r.json())
      .then((data) => {
        setRegistry(data)
        // Use URL params if provided, otherwise default to ethereum -> arbitrum
        const defaultSource = source || 'ethereum'
        const defaultDest = dest || 'arbitrum'
        
        // Validate that the chains exist in the registry
        if (data.networks[defaultSource] && data.networks[defaultDest]) {
          setSourceChain(defaultSource)
          setDestChain(defaultDest)
        } else {
          // Fallback to ethereum -> arbitrum if URL params are invalid
          setSourceChain('ethereum')
          setDestChain('arbitrum')
        }
      })
      .catch((e) => console.error('Failed to load CCIP registry:', e))
  }, [source, dest])

  useEffect(() => {
    if (!registry || !sourceChain || !destChain) return
    setLoading(true)
    setError(null)
    
    // Update URL to match selected chains
    const currentPath = `/products/ccip/${sourceChain}/${destChain}`
    if (window.location.pathname !== currentPath) {
      navigate(currentPath, { replace: true })
    }
    
    fetch(apiUrl(`/v1/ccip/lane/${sourceChain}/${destChain}`))
      .then(async (r) => {
        const data = await r.json()
        if (!r.ok) {
          setError(data.detail || 'Failed to load lane data')
          setLaneData(null)
        } else {
          setLaneData(data)
          setError(null)
        }
      })
      .catch((e) => {
        setError(String(e))
        setLaneData(null)
      })
      .finally(() => setLoading(false))
  }, [registry, sourceChain, destChain, navigate])

  const availableDestinations = registry?.networks[sourceChain]?.supports || []

  const soliditySnippet = laneData
    ? `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IRouterClient} from "@chainlink/contracts-ccip/contracts/interfaces/IRouterClient.sol";
import {Client} from "@chainlink/contracts-ccip/contracts/libraries/Client.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// Send CCIP messages from ${laneData.source.label} to ${laneData.destination.label}
/// Native fee token: ${laneData.source.native_fee_token || 'ETH'}
contract CCIPSender is Ownable {
    using SafeERC20 for IERC20;

    IRouterClient public immutable router;
    uint64 public constant DESTINATION_CHAIN_SELECTOR = ${laneData.destination.chain_selector};

    error InsufficientFee(uint256 required, uint256 provided);

    constructor() Ownable(msg.sender) {
        router = IRouterClient(${laneData.source.router});
    }

    /// Send a message (paying fee in native ${laneData.source.native_fee_token || 'ETH'})
    function sendMessage(
        address receiver,
        string memory message
    ) external payable onlyOwner returns (bytes32 messageId) {
        Client.EVM2AnyMessage memory evm2AnyMessage = Client.EVM2AnyMessage({
            receiver: abi.encode(receiver),
            data: abi.encode(message),
            tokenAmounts: new Client.EVMTokenAmount[](0),
            extraArgs: Client._argsToBytes(
                Client.GenericExtraArgsV2({gasLimit: 200_000, allowOutOfOrderExecution: true})
            ),
            feeToken: address(0) // Native token
        });

        uint256 fees = router.getFee(DESTINATION_CHAIN_SELECTOR, evm2AnyMessage);
        if (msg.value < fees) revert InsufficientFee(fees, msg.value);

        messageId = router.ccipSend{value: fees}(
            DESTINATION_CHAIN_SELECTOR,
            evm2AnyMessage
        );

        // Refund excess (use call, not transfer, to avoid 2300 gas limit issues)
        if (msg.value > fees) {
            (bool success, ) = msg.sender.call{value: msg.value - fees}("");
            require(success, "Refund failed");
        }
    }

    /// Send tokens (paying fee in native ${laneData.source.native_fee_token || 'ETH'})
    function sendTokens(
        address receiver,
        address token,
        uint256 amount
    ) external payable onlyOwner returns (bytes32 messageId) {
        // Use SafeERC20 for secure token transfers
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        IERC20(token).safeIncreaseAllowance(address(router), amount);

        Client.EVMTokenAmount[] memory tokenAmounts = new Client.EVMTokenAmount[](1);
        tokenAmounts[0] = Client.EVMTokenAmount({token: token, amount: amount});

        Client.EVM2AnyMessage memory evm2AnyMessage = Client.EVM2AnyMessage({
            receiver: abi.encode(receiver),
            data: "",
            tokenAmounts: tokenAmounts,
            extraArgs: Client._argsToBytes(
                Client.GenericExtraArgsV2({gasLimit: 0, allowOutOfOrderExecution: true})
            ),
            feeToken: address(0)
        });

        uint256 fees = router.getFee(DESTINATION_CHAIN_SELECTOR, evm2AnyMessage);
        if (msg.value < fees) revert InsufficientFee(fees, msg.value);

        messageId = router.ccipSend{value: fees}(
            DESTINATION_CHAIN_SELECTOR,
            evm2AnyMessage
        );

        if (msg.value > fees) {
            (bool success, ) = msg.sender.call{value: msg.value - fees}("");
            require(success, "Refund failed");
        }
    }

    /// Withdraw any tokens sent to this contract
    function withdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(msg.sender, amount);
    }

    receive() external payable {}
}

/// CCIP Receiver Example (deploy on ${laneData.destination.label})
import {IAny2EVMMessageReceiver} from "@chainlink/contracts-ccip/contracts/interfaces/IAny2EVMMessageReceiver.sol";
import {CCIPReceiver} from "@chainlink/contracts-ccip/contracts/applications/CCIPReceiver.sol";

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
}`
    : ''

  const javascriptSnippet = laneData
    ? `// npm install ethers
import { ethers } from "ethers";

const ROUTER = "${laneData.source.router}";
const DESTINATION_CHAIN_SELECTOR = "${laneData.destination.chain_selector}";

const ROUTER_ABI = [
  "function getFee(uint64 destinationChainSelector, tuple(bytes receiver, bytes data, tuple(address token, uint256 amount)[] tokenAmounts, address feeToken, bytes extraArgs) message) view returns (uint256)",
  "function ccipSend(uint64 destinationChainSelector, tuple(bytes receiver, bytes data, tuple(address token, uint256 amount)[] tokenAmounts, address feeToken, bytes extraArgs) message) payable returns (bytes32)"
];

const provider = new ethers.JsonRpcProvider("${laneData.source.rpc_urls?.[0] || 'YOUR_RPC_URL'}");
const wallet = new ethers.Wallet("YOUR_PRIVATE_KEY", provider);
const router = new ethers.Contract(ROUTER, ROUTER_ABI, wallet);

// Encode extraArgs with GENERIC_EXTRA_ARGS_V2_TAG (0x181dcf10)
function encodeExtraArgsV2(gasLimit, allowOutOfOrderExecution) {
  const abiCoder = ethers.AbiCoder.defaultAbiCoder();
  const encoded = abiCoder.encode(
    ["tuple(uint256 gasLimit, bool allowOutOfOrderExecution)"],
    [[gasLimit, allowOutOfOrderExecution]]
  );
  return ethers.concat(["0x181dcf10", encoded]); // Prepend V2 tag
}

// Encode message data
const receiverAddress = "0x..."; // Destination contract address
const message = "Hello CCIP!";

const ccipMessage = {
  receiver: ethers.AbiCoder.defaultAbiCoder().encode(["address"], [receiverAddress]),
  data: ethers.AbiCoder.defaultAbiCoder().encode(["string"], [message]),
  tokenAmounts: [],
  feeToken: ethers.ZeroAddress, // Pay in native token
  extraArgs: encodeExtraArgsV2(200000n, true)
};

// Get fee
const fee = await router.getFee(DESTINATION_CHAIN_SELECTOR, ccipMessage);
console.log("Fee:", ethers.formatEther(fee), "ETH");

// Preview the message ID using staticCall (read-only simulation)
const messageId = await router.ccipSend.staticCall(
  DESTINATION_CHAIN_SELECTOR,
  ccipMessage,
  { value: fee }
);
console.log("Message ID (preview):", messageId);

// Send the actual transaction
const tx = await router.ccipSend(DESTINATION_CHAIN_SELECTOR, ccipMessage, {
  value: fee
});
console.log("Transaction hash:", tx.hash);

await tx.wait();
console.log("Message sent successfully!");`
    : ''

  if (!registry) {
    return (
      <>
        <SEO 
          title="CCIP — Cross-Chain Interoperability Protocol"
          description="Explore CCIP lanes across 9 mainnets. Get router addresses, chain selectors, RMN proxies, and production-ready Solidity snippets for cross-chain messaging."
          path="/products/ccip"
        />
        <ProductLayout
          icon="🌉"
          title="CCIP"
          tagline="Cross-Chain Interoperability Protocol"
          status="live"
          description={<>Loading CCIP registry...</>}
        >
          <div className="flex items-center justify-center p-12">
            <div className="text-slate-400">Loading...</div>
          </div>
        </ProductLayout>
      </>
    )
  }

  const networks = Object.entries(registry.networks)
  
  // Generate SEO tags based on selected lane
  const seoTitle = laneData 
    ? `CCIP Lane: ${laneData.source.label} → ${laneData.destination.label}`
    : "CCIP — Cross-Chain Interoperability Protocol"
  const seoDescription = laneData
    ? `CCIP lane from ${laneData.source.label} to ${laneData.destination.label}. Router: ${laneData.source.router}, Chain Selector: ${laneData.destination.chain_selector}. Get production-ready Solidity snippets.`
    : "Explore CCIP lanes across 9 mainnets. Get router addresses, chain selectors, RMN proxies, and production-ready Solidity snippets for cross-chain messaging."
  const seoPath = source && dest ? `/products/ccip/${source}/${dest}` : "/products/ccip"

  return (
    <>
      <SEO 
        title={seoTitle}
        description={seoDescription}
        path={seoPath}
      />
      <ProductLayout
      icon="🌉"
      title="CCIP"
      tagline="Cross-Chain Interoperability Protocol"
      status="live"
      description={
        <>
          Explore CCIP lanes across {networks.length} mainnets. Get router addresses, chain selectors, RMN proxies, and
          production-ready Solidity snippets for cross-chain messaging and token transfers.
        </>
      }
    >
      <div className="p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          {/* Lane selector */}
          <div className="mb-6 rounded-2xl border border-ink-700 bg-ink-900">
            <div className="border-b border-ink-700 p-5">
              <h2 className="text-lg font-bold text-white">CCIP Lane Explorer</h2>
              <p className="mt-1 text-sm text-slate-400">
                Select source and destination chains to see router addresses, chain selectors, and integration code.
              </p>
            </div>

            <div className="grid gap-6 p-5 lg:grid-cols-2">
              {/* Source chain */}
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Source Chain
                </label>
                <select
                  value={sourceChain}
                  onChange={(e) => {
                    setSourceChain(e.target.value)
                    const newSupports = registry.networks[e.target.value]?.supports || []
                    if (!newSupports.includes(destChain)) {
                      setDestChain(newSupports[0] || '')
                    }
                  }}
                  className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-500"
                >
                  {networks.map(([id, n]) => (
                    <option key={id} value={id}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Destination chain */}
              <div>
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Destination Chain
                </label>
                <select
                  value={destChain}
                  onChange={(e) => setDestChain(e.target.value)}
                  className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-500"
                  disabled={availableDestinations.length === 0}
                >
                  {availableDestinations.map((chainId) => {
                    const chain = registry.networks[chainId]
                    return (
                      <option key={chainId} value={chainId}>
                        {chain.label}
                      </option>
                    )
                  })}
                </select>
                {availableDestinations.length === 0 && (
                  <p className="mt-1.5 text-xs text-rose-400">No supported destinations for this source chain</p>
                )}
              </div>
            </div>
          </div>

          {/* Error state */}
          {error && (
            <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/5 p-4">
              <p className="text-sm text-rose-400">{error}</p>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="mb-6 flex items-center justify-center rounded-xl border border-ink-700 bg-ink-900 p-8">
              <div className="text-sm text-slate-400">Loading lane data...</div>
            </div>
          )}

          {/* Lane data */}
          {laneData && !loading && (
            <>
              {/* Router addresses */}
              <div className="mb-6 rounded-2xl border border-ink-700 bg-ink-900">
                <div className="border-b border-ink-700 p-5">
                  <h3 className="text-base font-bold text-white">
                    Lane: {laneData.source.label} → {laneData.destination.label}
                  </h3>
                </div>

                <div className="grid gap-6 p-5 lg:grid-cols-2">
                  {/* Source */}
                  <div className="rounded-xl border border-ink-700 bg-ink-950 p-4">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold text-accent-300">
                      <span>📤</span>
                      <span>Source: {laneData.source.label}</span>
                    </h4>
                    <div className="space-y-2.5">
                      <div>
                        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          Chain Selector
                        </div>
                        <div className="group flex items-center gap-2">
                          <code className="flex-1 rounded bg-ink-900 px-2 py-1.5 font-mono text-[11px] text-slate-300">
                            {laneData.source.chain_selector}
                          </code>
                          <CopyButton text={laneData.source.chain_selector} className="px-2 py-1" />
                        </div>
                      </div>
                      <div>
                        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          Router Address
                        </div>
                        <div className="group flex items-center gap-2">
                          <code className="flex-1 rounded bg-ink-900 px-2 py-1.5 font-mono text-[11px] text-slate-300">
                            {laneData.source.router}
                          </code>
                          <CopyButton text={laneData.source.router} className="px-2 py-1" />
                        </div>
                      </div>
                      {laneData.source.rmn_proxy && (
                        <div>
                          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                            RMN Proxy
                          </div>
                          <div className="group flex items-center gap-2">
                            <code className="flex-1 rounded bg-ink-900 px-2 py-1.5 font-mono text-[11px] text-slate-300">
                              {laneData.source.rmn_proxy}
                            </code>
                            <CopyButton text={laneData.source.rmn_proxy} className="px-2 py-1" />
                          </div>
                        </div>
                      )}
                      <a
                        href={`${laneData.source.explorer}/address/${laneData.source.router}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1.5 text-xs text-accent-400 hover:text-accent-300"
                      >
                        View on Explorer
                        <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                          <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                        </svg>
                      </a>
                    </div>
                  </div>

                  {/* Destination */}
                  <div className="rounded-xl border border-ink-700 bg-ink-950 p-4">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold text-emerald-300">
                      <span>📥</span>
                      <span>Destination: {laneData.destination.label}</span>
                    </h4>
                    <div className="space-y-2.5">
                      <div>
                        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          Chain Selector
                        </div>
                        <div className="group flex items-center gap-2">
                          <code className="flex-1 rounded bg-ink-900 px-2 py-1.5 font-mono text-[11px] text-slate-300">
                            {laneData.destination.chain_selector}
                          </code>
                          <CopyButton text={laneData.destination.chain_selector} className="px-2 py-1" />
                        </div>
                      </div>
                      <div>
                        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          Router Address
                        </div>
                        <div className="group flex items-center gap-2">
                          <code className="flex-1 rounded bg-ink-900 px-2 py-1.5 font-mono text-[11px] text-slate-300">
                            {laneData.destination.router}
                          </code>
                          <CopyButton text={laneData.destination.router} className="px-2 py-1" />
                        </div>
                      </div>
                      {laneData.destination.rmn_proxy && (
                        <div>
                          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                            RMN Proxy
                          </div>
                          <div className="group flex items-center gap-2">
                            <code className="flex-1 rounded bg-ink-900 px-2 py-1.5 font-mono text-[11px] text-slate-300">
                              {laneData.destination.rmn_proxy}
                            </code>
                            <CopyButton text={laneData.destination.rmn_proxy} className="px-2 py-1" />
                          </div>
                        </div>
                      )}
                      <a
                        href={`${laneData.destination.explorer}/address/${laneData.destination.router}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1.5 text-xs text-accent-400 hover:text-accent-300"
                      >
                        View on Explorer
                        <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                          <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                        </svg>
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              {/* Code snippets */}
              <div className="rounded-2xl border border-ink-700 bg-ink-900">
                <div className="border-b border-ink-700 p-5">
                  <h3 className="text-base font-bold text-white">Integration Snippets</h3>
                  <p className="mt-1 text-sm text-slate-400">
                    Production-ready code for sending messages and tokens via CCIP.
                  </p>
                </div>

                <div className="divide-y divide-ink-700">
                  {/* Solidity */}
                  <div className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h4 className="text-sm font-bold text-slate-300">Solidity</h4>
                      <CopyButton text={soliditySnippet} />
                    </div>
                    <pre className="overflow-x-auto rounded-lg bg-ink-950 p-4 font-mono text-[11px] leading-relaxed text-slate-300">
                      {soliditySnippet}
                    </pre>
                  </div>

                  {/* JavaScript */}
                  <div className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h4 className="text-sm font-bold text-slate-300">JavaScript (Ethers.js)</h4>
                      <CopyButton text={javascriptSnippet} />
                    </div>
                    <pre className="overflow-x-auto rounded-lg bg-ink-950 p-4 font-mono text-[11px] leading-relaxed text-slate-300">
                      {javascriptSnippet}
                    </pre>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Resources */}
          <div className="mt-6 rounded-xl border border-accent-500/30 bg-accent-500/5 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">Resources</h3>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://docs.chain.link/ccip"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                CCIP Documentation
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
              <a
                href="https://docs.chain.link/ccip/directory/mainnet"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                CCIP Mainnet Directory
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </ProductLayout>
    </>
  )
}
