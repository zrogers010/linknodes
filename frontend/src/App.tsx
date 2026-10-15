import { useEffect, useMemo, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { apiUrl } from './config'
import { FeedIndexPage } from './pages/FeedIndexPage'
import { FeedDetailPage } from './pages/FeedDetailPage'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OperatorsPage } from './pages/OperatorsPage'
import { AutomationPage } from './pages/products/AutomationPage'
import { CCIPPage } from './pages/products/CCIPPage'
import { DataFeedsPage } from './pages/products/DataFeedsPage'
import { FunctionsPage } from './pages/products/FunctionsPage'
import { VRFPage } from './pages/products/VRFPage'
import { EnvironmentProvider, useEnvironment } from './EnvironmentContext'
import { ChartBarIcon, NetworkIcon, CodeIcon, DicesIcon, ClockIcon, HexagonIcon } from './components/icons/Icon'
import type { Registry } from './types'

const PRODUCT_NAV = [
  { to: '/products/data-feeds', label: 'Data Feeds', icon: ChartBarIcon },
  { to: '/products/ccip', label: 'CCIP', icon: NetworkIcon },
  { to: '/products/functions', label: 'Functions', icon: CodeIcon },
  { to: '/products/vrf', label: 'VRF', icon: DicesIcon },
  { to: '/products/automation', label: 'Automation', icon: ClockIcon },
]

const SECONDARY_NAV = [
  { to: '/feeds', label: 'Feed Catalog', end: false },
  { to: '/operators', label: 'Node Operators', end: false },
]

function Navigation({ registry }: { registry: Registry }) {
  const location = useLocation()
  const isProductPage = location.pathname.startsWith('/products/')
  const { environment, setEnvironment } = useEnvironment()
  
  const totalFeeds = useMemo(
    () => Object.values(registry.networks).reduce((sum, n) => sum + n.feed_count, 0),
    [registry],
  )

  return (
    <header className="shrink-0 border-b border-ink-700 bg-ink-900">
      <div className="flex items-center gap-3 px-4 py-2.5 sm:px-5">
        <Link to="/" className="flex h-7 w-7 shrink-0 items-center justify-center border border-ink-600 bg-ink-800 text-accent-400 transition-colors hover:border-accent-500 hover:text-accent-300">
          <HexagonIcon size={16} />
        </Link>
        <div className="min-w-0">
          <Link to="/" className="group">
            <h1 className="text-sm font-bold leading-tight tracking-tight text-white transition-colors group-hover:text-accent-300">
              LinkNodes<span className="text-slate-500">.io</span>
            </h1>
          </Link>
          <p className="hidden text-[10px] leading-tight text-slate-500 sm:block">
            Chainlink developer toolkit
          </p>
        </div>

        {!isProductPage && (
          <nav className="ml-2 hidden items-center gap-1 sm:ml-8 sm:flex">
            {SECONDARY_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `px-3 py-1.5 text-xs font-medium transition-colors ${
                    isActive
                      ? 'text-accent-400'
                      : 'text-slate-400 hover:text-slate-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setEnvironment(environment === 'mainnet' ? 'testnet' : 'mainnet')}
            className="border border-ink-600 bg-ink-800 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-slate-300 transition-colors hover:border-ink-500 hover:bg-ink-750"
            title="Toggle between Mainnet and Testnet"
          >
            {environment === 'mainnet' ? 'Mainnet' : 'Testnet'}
          </button>
          <span className="hidden border border-ink-600 bg-ink-800 px-2.5 py-1 font-mono text-[10px] text-slate-400 lg:inline">
            {totalFeeds.toLocaleString()} feeds · {Object.keys(registry.networks).length} chains
          </span>
        </div>
      </div>

      {/* Product navigation */}
      {isProductPage && (
        <nav className="flex items-center gap-px overflow-x-auto border-t border-ink-700 bg-ink-950 px-3 sm:px-5">
          {PRODUCT_NAV.map((item) => {
            const IconComponent = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
                    isActive
                      ? 'border-accent-500 text-accent-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`
                }
              >
                <IconComponent size={14} />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      )}
      
      {/* Mobile secondary nav row */}
      {!isProductPage && (
        <nav className="flex items-center gap-1 border-t border-ink-700 px-3 py-1.5 sm:hidden">
          {SECONDARY_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex-1 px-3 py-1.5 text-center text-xs font-medium transition-colors ${
                  isActive
                    ? 'text-accent-400'
                    : 'text-slate-400 hover:text-slate-200'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}

export default function App() {
  const [registry, setRegistry] = useState<Registry | null>(null)
  const [registryError, setRegistryError] = useState<string | null>(null)

  useEffect(() => {
    fetch(apiUrl('/v1/registry'))
      .then((r) => {
        if (!r.ok) throw new Error(`registry fetch failed: HTTP ${r.status}`)
        return r.json()
      })
      .then(setRegistry)
      .catch((e) => setRegistryError(String(e)))
  }, [])

  if (registryError) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="max-w-md rounded-xl border border-rose-500/30 bg-ink-900 p-6 text-center">
          <p className="text-sm font-semibold text-rose-400">Engine unreachable</p>
          <p className="mt-2 font-mono text-[12px] text-slate-400">{registryError}</p>
          <p className="mt-3 text-[12px] text-slate-500">
            Start the backend: <code className="text-slate-300">uvicorn main:app --port 8100</code>
          </p>
        </div>
      </div>
    )
  }

  if (!registry) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="font-mono text-sm text-slate-500">loading feed catalog…</p>
      </div>
    )
  }

  return (
    <EnvironmentProvider>
      <BrowserRouter>
        <div className="flex h-full flex-col">
          <Navigation registry={registry} />

          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/products/data-feeds" element={<DataFeedsPage registry={registry} />} />
            <Route path="/products/ccip" element={<CCIPPage />} />
            <Route path="/products/ccip/:source/:dest" element={<CCIPPage />} />
            <Route path="/products/functions" element={<FunctionsPage />} />
            <Route path="/products/vrf" element={<VRFPage />} />
            <Route path="/products/automation" element={<AutomationPage />} />
            <Route path="/feeds" element={<FeedIndexPage />} />
            <Route path="/feeds/:chain" element={<FeedIndexPage />} />
            <Route path="/feeds/:chain/:feed" element={<FeedDetailPage />} />
            <Route path="/operators" element={<OperatorsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </EnvironmentProvider>
  )
}
