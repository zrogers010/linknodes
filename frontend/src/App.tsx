import { useEffect, useMemo, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { FeedsPage } from './pages/FeedsPage'
import { OperatorsPage } from './pages/OperatorsPage'
import { SandboxPage } from './pages/SandboxPage'
import type { Registry } from './types'

const NAV = [
  { to: '/', label: 'Sandbox', end: true },
  { to: '/feeds', label: 'Feed Catalog', end: false },
  { to: '/operators', label: 'Node Operators', end: false },
]

export default function App() {
  const [registry, setRegistry] = useState<Registry | null>(null)
  const [registryError, setRegistryError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/v1/registry')
      .then((r) => {
        if (!r.ok) throw new Error(`registry fetch failed: HTTP ${r.status}`)
        return r.json()
      })
      .then(setRegistry)
      .catch((e) => setRegistryError(String(e)))
  }, [])

  const totalFeeds = useMemo(
    () =>
      registry ? Object.values(registry.networks).reduce((sum, n) => sum + n.feed_count, 0) : 0,
    [registry],
  )

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
    <BrowserRouter>
      <div className="flex h-full flex-col">
        <header className="border-b border-ink-700 bg-ink-900">
          <div className="flex items-center gap-3 px-4 py-3 sm:px-5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-500 font-mono text-sm font-black text-white shadow-lg shadow-accent-500/30">
              ⛓
            </div>
            <div className="min-w-0">
              <h1 className="text-[15px] font-bold leading-tight tracking-tight text-white">
                LinkNodes<span className="text-accent-400">.io</span>
              </h1>
              <p className="hidden text-[11px] leading-tight text-slate-500 sm:block">
                The oracle query sandbox for Chainlink developers
              </p>
            </div>

            <nav className="ml-2 hidden items-center gap-1 sm:ml-8 sm:flex">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
                      isActive
                        ? 'bg-accent-500/15 text-accent-300'
                        : 'text-slate-400 hover:bg-ink-800 hover:text-slate-200'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-2">
              <span className="hidden rounded-full border border-ink-600 bg-ink-800 px-2.5 py-1 font-mono text-[10px] text-slate-400 lg:inline">
                {totalFeeds.toLocaleString()} feeds · {Object.keys(registry.networks).length} chains
              </span>
              <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-400 md:inline">
                Free · No keys · No accounts
              </span>
            </div>
          </div>

          {/* Mobile nav row */}
          <nav className="flex items-center gap-1 px-3 pb-2 sm:hidden">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex-1 rounded-lg px-3 py-1.5 text-center text-[13px] font-medium transition-colors ${
                    isActive
                      ? 'bg-accent-500/15 text-accent-300'
                      : 'text-slate-400 hover:bg-ink-800 hover:text-slate-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<SandboxPage registry={registry} />} />
          <Route path="/feeds" element={<FeedsPage registry={registry} />} />
          <Route path="/operators" element={<OperatorsPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
