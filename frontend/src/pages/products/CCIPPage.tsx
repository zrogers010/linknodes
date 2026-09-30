import { useState } from 'react'
import { ProductLayout } from '../../components/ProductLayout'

const SUPPORTED_CHAINS = [
  { name: 'Ethereum', id: 'ethereum', selector: '5009297550715157269' },
  { name: 'Arbitrum', id: 'arbitrum', selector: '4949039107694359620' },
  { name: 'Optimism', id: 'optimism', selector: '3734403246176062136' },
  { name: 'Base', id: 'base', selector: '15971525489660198786' },
  { name: 'Polygon', id: 'polygon', selector: '4051577828743386545' },
  { name: 'Avalanche', id: 'avalanche', selector: '6433500567565415381' },
]

export function CCIPPage() {
  const [sourceChain, setSourceChain] = useState('arbitrum')
  const [destChain, setDestChain] = useState('base')
  const [message, setMessage] = useState('Hello CCIP!')
  
  return (
    <ProductLayout
      icon="🌉"
      title="CCIP"
      tagline="Cross-Chain Interoperability Protocol"
      status="preview"
      description={
        <>
          Send tokens and arbitrary messages across blockchains with Chainlink CCIP. Build multi-chain dApps, enable cross-chain token transfers, and unlock interoperability with a single unified interface.
        </>
      }
    >
      <div className="p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          {/* Overview cards */}
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">🔒</div>
              <h3 className="mb-1 text-sm font-bold text-white">Secure by design</h3>
              <p className="text-xs text-slate-400">
                Multi-layered security with Risk Management Network and Active Risk Management for every transfer
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">⚡</div>
              <h3 className="mb-1 text-sm font-bold text-white">Simplified UX</h3>
              <p className="text-xs text-slate-400">
                One contract call to send tokens and data across chains — no bridges, no wrapped assets, no complexity
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">🌐</div>
              <h3 className="mb-1 text-sm font-bold text-white">Growing network</h3>
              <p className="text-xs text-slate-400">
                Live on 15+ mainnets with billions in value transferred securely across chains
              </p>
            </div>
          </div>

          {/* Interactive section */}
          <div className="rounded-2xl border border-ink-700 bg-ink-900">
            <div className="border-b border-ink-700 p-5">
              <h2 className="text-lg font-bold text-white">Message Builder (Preview)</h2>
              <p className="mt-1 text-sm text-slate-400">
                Simulate cross-chain message construction. Full sandbox with live testnet integration coming soon.
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
                  onChange={(e) => setSourceChain(e.target.value)}
                  className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 text-sm text-slate-200 outline-none focus:border-accent-500"
                >
                  {SUPPORTED_CHAINS.map((chain) => (
                    <option key={chain.id} value={chain.id}>
                      {chain.name}
                    </option>
                  ))}
                </select>
                <p className="mt-1.5 font-mono text-xs text-slate-500">
                  Selector: {SUPPORTED_CHAINS.find(c => c.id === sourceChain)?.selector}
                </p>
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
                >
                  {SUPPORTED_CHAINS.filter(c => c.id !== sourceChain).map((chain) => (
                    <option key={chain.id} value={chain.id}>
                      {chain.name}
                    </option>
                  ))}
                </select>
                <p className="mt-1.5 font-mono text-xs text-slate-500">
                  Selector: {SUPPORTED_CHAINS.find(c => c.id === destChain)?.selector}
                </p>
              </div>

              {/* Message content */}
              <div className="lg:col-span-2">
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Message Data
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Enter message to send cross-chain..."
                  rows={3}
                  className="w-full rounded-lg border border-ink-600 bg-ink-800 px-4 py-2.5 font-mono text-sm text-slate-200 outline-none focus:border-accent-500"
                />
              </div>
            </div>

            {/* Generated code preview */}
            <div className="border-t border-ink-700 bg-ink-950 p-5">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Generated Message Structure
              </h3>
              <pre className="overflow-x-auto rounded-lg bg-ink-900 p-4 font-mono text-xs text-slate-300">
{JSON.stringify({
  sourceChain: SUPPORTED_CHAINS.find(c => c.id === sourceChain)?.name,
  sourceChainSelector: SUPPORTED_CHAINS.find(c => c.id === sourceChain)?.selector,
  destinationChain: SUPPORTED_CHAINS.find(c => c.id === destChain)?.name,
  destinationChainSelector: SUPPORTED_CHAINS.find(c => c.id === destChain)?.selector,
  message: message || '(empty)',
  messageId: '0x...',
  status: 'pending',
}, null, 2)}
              </pre>
            </div>
          </div>

          {/* Use cases */}
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-bold text-white">Popular Use Cases</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>💱</span>
                  <span>Cross-chain DEX</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Swap tokens across chains in a single transaction. Trade ETH on Ethereum for USDC on Arbitrum without manual bridging.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎮</span>
                  <span>Multi-chain gaming</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Build games where assets live on different chains. Transfer NFTs, currency, and game state seamlessly.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🏦</span>
                  <span>Cross-chain lending</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Collateralize assets on one chain to borrow on another. Unlock capital efficiency across ecosystems.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🔔</span>
                  <span>Chain-agnostic notifications</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Send event data from one chain to trigger actions on others. Build truly interoperable protocols.
                </p>
              </div>
            </div>
          </div>

          {/* Resources */}
          <div className="mt-8 rounded-xl border border-accent-500/30 bg-accent-500/5 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">Coming Soon: Full Interactive Sandbox</h3>
            <p className="mb-4 text-sm text-slate-400">
              We're building a complete CCIP sandbox with live testnet integration, message tracking, and fee estimation. In the meantime, explore the official documentation:
            </p>
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
                href="https://docs.chain.link/ccip/tutorials"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                CCIP Tutorials
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
  )
}
