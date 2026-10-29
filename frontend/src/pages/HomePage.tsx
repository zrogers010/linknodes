import { Link } from 'react-router-dom'
import { SEO } from '../components/SEO'
import { ChartBarIcon, NetworkIcon, CodeIcon, DicesIcon, ClockIcon, CheckIcon, ChevronRightIcon } from '../components/icons/Icon'

const PRODUCTS = [
  {
    id: 'data-feeds',
    name: 'Data Feeds',
    icon: ChartBarIcon,
    tagline: 'Price oracle sandbox',
    description: 'Query 1,400+ live price feeds across 13 mainnets. Browse crypto, forex, equities, commodities, and economic data with historical rounds and aggregation details.',
    status: 'live',
    features: ['1,400+ feeds', '13 mainnets', 'Historical data', 'Live queries'],
  },
  {
    id: 'ccip',
    name: 'CCIP',
    icon: NetworkIcon,
    tagline: 'Cross-chain messaging',
    description: 'Explore CCIP lanes across 9 mainnets. View router addresses, chain selectors, RMN proxies, and copy Solidity integration snippets for message and token transfers.',
    status: 'live',
    features: ['Router addresses', 'Chain selectors', 'Code snippets', '9 mainnets'],
  },
  {
    id: 'functions',
    name: 'Functions',
    icon: CodeIcon,
    tagline: 'Serverless compute',
    description: 'Execute custom JavaScript on Chainlink DON. Fetch external APIs, run computations, and connect any off-chain data source to your smart contracts.',
    status: 'preview',
    features: ['Any API call', 'Custom JS logic', 'Secrets management', 'DON execution'],
  },
  {
    id: 'vrf',
    name: 'VRF',
    icon: DicesIcon,
    tagline: 'Verifiable randomness',
    description: 'Generate cryptographically provable random numbers on-chain. On-chain verification ensures results cannot be manipulated by miners, validators, or node operators.',
    status: 'preview',
    features: ['Cryptographic proof', 'On-chain verification', 'Fast finality', 'Gas-efficient'],
  },
  {
    id: 'automation',
    name: 'Automation',
    icon: ClockIcon,
    tagline: 'Decentralized keepers',
    description: 'Trigger smart contract functions automatically based on time schedules or custom conditions. Off-load maintenance tasks and state transitions from manual EOA calls.',
    status: 'preview',
    features: ['Time-based triggers', 'Custom logic', 'Gas optimization', 'Reliable execution'],
  },
]

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  live: { label: 'Live', className: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' },
  preview: { label: 'Coming Soon', className: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
}

export function HomePage() {
  return (
    <main className="min-h-0 flex-1 overflow-y-auto">
      <SEO 
        title="Chainlink Developer Toolkit — LinkNodes"
        description="Query 1,400+ live Chainlink Data Feeds and explore CCIP lane configuration across 13 mainnets. Free developer toolkit, no wallet required."
        path="/"
      />
      {/* Hero section */}
      <section className="border-b border-ink-700 bg-ink-900">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16 lg:py-20">
          <div className="max-w-3xl">
            <div className="mb-3 inline-block border border-ink-600 bg-ink-800 px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-slate-400">
              Developer Toolkit
            </div>
            <h1 className="mb-4 text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-5xl">
              Chainlink oracle sandbox and integration tools
            </h1>
            <p className="mb-6 max-w-2xl text-base leading-relaxed text-slate-400">
              Query 1,400+ live Data Feeds across 13 mainnets, explore CCIP router configuration for 9 chains, and copy production-ready integration snippets. No wallet or testnet tokens required.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                to="/products/data-feeds"
                className="inline-flex items-center gap-2 border border-accent-500 bg-accent-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-600"
              >
                Data Feeds Sandbox
                <ChevronRightIcon size={16} />
              </Link>
              <Link
                to="/products/ccip"
                className="inline-flex items-center gap-2 border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-300 transition-colors hover:border-ink-500 hover:bg-ink-750"
              >
                CCIP Explorer
                <ChevronRightIcon size={16} />
              </Link>
              <Link
                to="/rwa"
                className="inline-flex items-center gap-2 border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-300 transition-colors hover:border-ink-500 hover:bg-ink-750"
              >
                RWA / 24/7
                <ChevronRightIcon size={16} />
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-4 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <CheckIcon size={14} className="text-slate-400" />
                <span>Free, no account</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckIcon size={14} className="text-slate-400" />
                <span>Live mainnet data</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckIcon size={14} className="text-slate-400" />
                <span>Open source</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product grid */}
      <section className="border-b border-ink-700 bg-ink-950">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
          <div className="mb-8">
            <h2 className="mb-2 text-xl font-bold text-white">Available Tools</h2>
            <p className="max-w-2xl text-sm text-slate-400">
              Data Feeds sandbox with 1,400+ feeds across 13 mainnets. CCIP lane explorer with router addresses and Solidity snippets. Additional services in development.
            </p>
          </div>
          
          <div className="grid gap-4 sm:grid-cols-2">
            {PRODUCTS.map((product) => {
              const statusBadge = STATUS_BADGE[product.status]
              const IconComponent = product.icon
              return (
                <Link
                  key={product.id}
                  to={`/products/${product.id}`}
                  className="group relative flex flex-col border border-ink-700 bg-ink-900 p-5 transition-colors hover:border-ink-600 hover:bg-ink-850"
                >
                  <div className="mb-3 flex items-start justify-between">
                    <div className="flex h-9 w-9 items-center justify-center border border-ink-600 bg-ink-800 text-accent-400">
                      <IconComponent size={18} />
                    </div>
                    <span className={`border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${statusBadge.className}`}>
                      {statusBadge.label}
                    </span>
                  </div>
                  
                  <h3 className="mb-1 text-base font-bold text-white">
                    {product.name}
                  </h3>
                  <p className="mb-2 text-xs font-medium text-slate-400">
                    {product.tagline}
                  </p>
                  <p className="mb-3 text-xs leading-relaxed text-slate-500">
                    {product.description}
                  </p>
                  
                  <div className="mt-auto">
                    <div className="mb-2 grid grid-cols-2 gap-x-3 gap-y-1">
                      {product.features.map((feature) => (
                        <div key={feature} className="flex items-center gap-1 text-[11px] text-slate-500">
                          <div className="h-1 w-1 shrink-0 bg-slate-600" />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center gap-1.5 pt-1 text-xs font-medium text-accent-400 transition-colors group-hover:text-accent-300">
                      <span>{product.status === 'live' ? 'Open sandbox' : 'View documentation'}</span>
                      <ChevronRightIcon size={12} />
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      {/* Quick facts */}
      <section className="bg-ink-950">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
          <div className="grid gap-px bg-ink-700 sm:grid-cols-2">
            <div className="bg-ink-900 p-5">
              <h3 className="mb-2 text-sm font-bold text-white">Why LinkNodes</h3>
              <p className="text-xs leading-relaxed text-slate-400">
                Official Chainlink documentation teaches oracle concepts and contract interfaces. LinkNodes provides interactive sandboxes where you can query live feeds, inspect CCIP router configuration, and copy integration code without setting up wallets or testnets.
              </p>
            </div>
            
            <div className="bg-ink-900 p-5">
              <h3 className="mb-2 text-sm font-bold text-white">How it works</h3>
              <p className="text-xs leading-relaxed text-slate-400">
                All queries run against live mainnet contracts using free public RPC endpoints. No authentication, no wallet signatures, no testnet faucets. Select a feed or CCIP lane, view current data and router addresses, then copy the Solidity or JavaScript snippet for your project.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA section */}
      <section className="border-t border-ink-700 bg-ink-900">
        <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
          <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="mb-1 text-lg font-bold text-white">Start with Data Feeds</h2>
              <p className="text-xs text-slate-400">
                Query 1,400+ price feeds across Ethereum, Arbitrum, Optimism, Base, Polygon, BNB Chain, Avalanche, and 6 other mainnets.
              </p>
            </div>
            <Link
              to="/products/data-feeds"
              className="inline-flex shrink-0 items-center gap-2 border border-accent-500 bg-accent-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-600"
            >
              Open Sandbox
              <ChevronRightIcon size={16} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  )
}
