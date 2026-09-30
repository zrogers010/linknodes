import { Link } from 'react-router-dom'

const PRODUCTS = [
  {
    id: 'data-feeds',
    name: 'Data Feeds',
    icon: '📊',
    tagline: 'Real-time price oracles',
    description: 'Query 1,400+ live price feeds across 13 chains. Get crypto, forex, equities, commodities, and macro data on-chain with sub-minute updates.',
    status: 'live',
    features: ['1,400+ feeds', '13 mainnets', 'Sub-second latency', 'Historical rounds'],
  },
  {
    id: 'ccip',
    name: 'CCIP',
    icon: '🌉',
    tagline: 'Cross-chain interoperability',
    description: 'Send tokens and arbitrary messages across blockchains. Build cross-chain dApps with Chainlink\'s secure messaging protocol.',
    status: 'preview',
    features: ['Token transfers', 'Message passing', 'Multi-chain apps', 'Programmable transfers'],
  },
  {
    id: 'functions',
    name: 'Functions',
    icon: '⚡',
    tagline: 'Serverless Web2 compute',
    description: 'Execute custom JavaScript on Chainlink\'s decentralized oracle network. Fetch APIs, run computations, and bring any off-chain data on-chain.',
    status: 'preview',
    features: ['Any API call', 'Custom JS logic', 'Secrets management', 'Decentralized execution'],
  },
  {
    id: 'vrf',
    name: 'VRF',
    icon: '🎲',
    tagline: 'Verifiable randomness',
    description: 'Generate provably fair random numbers on-chain. Perfect for NFT mints, gaming, lotteries, and any application requiring tamper-proof randomness.',
    status: 'preview',
    features: ['Cryptographic proof', 'On-chain verification', 'Instant finality', 'Gas-efficient'],
  },
  {
    id: 'automation',
    name: 'Automation',
    icon: '🤖',
    tagline: 'Decentralized keepers',
    description: 'Trigger smart contract functions automatically based on time or custom conditions. Automate DeFi strategies, NFT reveals, and maintenance tasks.',
    status: 'preview',
    features: ['Time-based triggers', 'Custom logic', 'Gas optimization', 'Reliable execution'],
  },
]

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  live: { label: 'Live Sandbox', className: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  preview: { label: 'Preview', className: 'bg-sky-500/15 text-sky-400 border-sky-500/30' },
}

export function HomePage() {
  return (
    <main className="min-h-0 flex-1 overflow-y-auto">
      {/* Hero section */}
      <section className="border-b border-ink-700 bg-gradient-to-b from-ink-900 to-ink-950">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20 lg:py-24">
          <div className="text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-accent-500/30 bg-accent-500/10 px-4 py-1.5 text-sm">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-500"></span>
              </span>
              <span className="font-semibold text-accent-300">The Developer Toolkit for Chainlink</span>
            </div>
            <h1 className="mb-5 text-4xl font-black leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
              Test, debug, and ship
              <br />
              <span className="bg-gradient-to-r from-accent-300 to-accent-500 bg-clip-text text-transparent">
                Chainlink integrations
              </span>
            </h1>
            <p className="mx-auto mb-8 max-w-2xl text-lg leading-relaxed text-slate-400 sm:text-xl">
              Interactive sandboxes for every Chainlink service. Query live feeds, simulate cross-chain messages, test Functions, generate VRF randomness, and automate contracts — all in your browser, no wallet required.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link
                to="/products/data-feeds"
                className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-6 py-3 text-base font-bold text-white shadow-lg shadow-accent-500/30 transition-all hover:bg-accent-600 hover:shadow-accent-500/40"
              >
                Try Data Feeds Sandbox
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </Link>
              <a
                href="https://github.com/zrogers010/linknodes"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-6 py-3 text-base font-semibold text-slate-200 transition-colors hover:border-ink-500 hover:bg-ink-700"
              >
                View on GitHub
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" clipRule="evenodd" />
                </svg>
              </a>
            </div>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500">
              <div className="flex items-center gap-2">
                <svg className="h-4 w-4 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Free forever</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="h-4 w-4 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>No wallet required</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="h-4 w-4 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Open source</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product grid */}
      <section className="border-b border-ink-700 bg-ink-950">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
          <div className="mb-10 text-center">
            <h2 className="mb-3 text-3xl font-black text-white">Complete Chainlink Suite</h2>
            <p className="mx-auto max-w-2xl text-slate-400">
              Every Chainlink service, one developer toolkit. Build faster with interactive sandboxes, instant feedback, and production-ready code snippets.
            </p>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {PRODUCTS.map((product) => {
              const statusBadge = STATUS_BADGE[product.status]
              return (
                <Link
                  key={product.id}
                  to={`/products/${product.id}`}
                  className="group relative flex flex-col rounded-2xl border border-ink-700 bg-ink-900 p-6 transition-all hover:border-accent-500/50 hover:shadow-xl hover:shadow-accent-500/10"
                >
                  <div className="mb-4 flex items-start justify-between">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500/20 to-accent-600/20 text-2xl shadow-lg shadow-accent-500/20">
                      {product.icon}
                    </div>
                    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${statusBadge.className}`}>
                      {statusBadge.label}
                    </span>
                  </div>
                  
                  <h3 className="mb-2 text-xl font-bold text-white group-hover:text-accent-300">
                    {product.name}
                  </h3>
                  <p className="mb-3 text-sm font-semibold text-accent-400">
                    {product.tagline}
                  </p>
                  <p className="mb-4 text-sm leading-relaxed text-slate-400">
                    {product.description}
                  </p>
                  
                  <div className="mt-auto space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      {product.features.map((feature) => (
                        <div key={feature} className="flex items-center gap-1.5 text-xs text-slate-500">
                          <svg className="h-3.5 w-3.5 shrink-0 text-accent-500" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center gap-2 pt-2 text-sm font-semibold text-accent-300 transition-transform group-hover:translate-x-1">
                      <span>{product.status === 'live' ? 'Launch sandbox' : 'Explore preview'}</span>
                      <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      {/* Positioning section */}
      <section className="bg-ink-950">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="grid gap-8 md:grid-cols-2">
            <div className="rounded-2xl border border-ink-700 bg-ink-900 p-8">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500/20 text-xl">
                🚀
              </div>
              <h3 className="mb-3 text-xl font-bold text-white">For developers, by developers</h3>
              <p className="mb-4 text-slate-400">
                LinkNodes is the missing developer experience layer for Chainlink. While docs.chain.link teaches concepts, LinkNodes lets you experiment instantly — query real feeds, test message flows, and grab production snippets without leaving your browser.
              </p>
              <p className="text-sm text-slate-500">
                Think Postman for Chainlink: iterate faster, debug smarter, ship with confidence.
              </p>
            </div>
            
            <div className="rounded-2xl border border-ink-700 bg-ink-900 p-8">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500/20 text-xl">
                ⚡
              </div>
              <h3 className="mb-3 text-xl font-bold text-white">Instant feedback, zero friction</h3>
              <p className="mb-4 text-slate-400">
                No wallet setup, no test tokens, no spinning up local nodes. Every sandbox runs on live mainnets with real data, using free public RPCs. Go from landing page to working integration in under 60 seconds.
              </p>
              <p className="text-sm text-slate-500">
                Free forever, open source, and built for the community.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA section */}
      <section className="border-t border-ink-700 bg-gradient-to-b from-ink-950 to-ink-900">
        <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:px-6">
          <h2 className="mb-4 text-3xl font-black text-white">Ready to build?</h2>
          <p className="mb-8 text-lg text-slate-400">
            Start with Data Feeds — the most battle-tested oracle service in DeFi.
          </p>
          <Link
            to="/products/data-feeds"
            className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-8 py-4 text-lg font-bold text-white shadow-xl shadow-accent-500/30 transition-all hover:bg-accent-600 hover:shadow-accent-500/40"
          >
            Launch Data Feeds Sandbox
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </Link>
        </div>
      </section>
    </main>
  )
}
