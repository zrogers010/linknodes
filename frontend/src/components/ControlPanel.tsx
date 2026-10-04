import { useMemo, useState } from 'react'
import { popularityScore } from '../popularity'
import type { Registry, SandboxState } from '../types'

const MAX_VISIBLE = 120

const TYPE_EMOJI: Record<string, string> = {
  Crypto: '🪙',
  Forex: '💱',
  Commodities: '🛢️',
  Equities: '📈',
  Fiat: '💵',
  Macroeconomics: '🏛️',
}

const CATEGORY_STYLE: Record<string, string> = {
  low: 'text-emerald-400',
  medium: 'text-amber-400',
  high: 'text-rose-400',
  new: 'text-sky-400',
  custom: 'text-violet-400',
  unranked: 'text-slate-500',
}

interface Props {
  registry: Registry
  state: SandboxState
  onChange: (patch: Partial<SandboxState>) => void
  /** Called after a feed is chosen (used to close the mobile drawer). */
  onFeedPick?: () => void
}

export function ControlPanel({ registry, state, onChange, onFeedPick }: Props) {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('All')

  const net = registry.networks[state.network]

  const feedTypes = useMemo(() => {
    const counts = new Map<string, number>()
    for (const feed of Object.values(net?.feeds ?? {})) {
      counts.set(feed.feed_type, (counts.get(feed.feed_type) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t)
  }, [net])

  const matches = useMemo(() => {
    const q = search.trim().toLowerCase()
    return Object.entries(net?.feeds ?? {})
      .filter(([slug, feed]) => {
        if (typeFilter !== 'All' && feed.feed_type !== typeFilter) return false
        if (!q) return true
        return (
          slug.includes(q) ||
          feed.name.toLowerCase().includes(q) ||
          feed.asset_name.toLowerCase().includes(q) ||
          feed.address.toLowerCase().includes(q)
        )
      })
      .sort(
        ([slugA, feedA], [slugB, feedB]) =>
          popularityScore(slugB, 0) - popularityScore(slugA, 0) ||
          feedA.name.localeCompare(feedB.name),
      )
  }, [net, search, typeFilter])

  const visible = matches.slice(0, MAX_VISIBLE)

  return (
    <aside className="flex h-full min-h-0 flex-col border-r border-ink-700 bg-ink-900">
      <div className="border-b border-ink-700 p-4">
        <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          Target Network
        </label>
        <div className="relative">
          <select
            value={state.network}
            onChange={(e) => onChange({ network: e.target.value })}
            className="w-full appearance-none rounded-lg border border-ink-600 bg-ink-800 px-3 py-2.5 text-sm font-medium text-slate-200 outline-none transition-colors hover:border-accent-500/60 focus:border-accent-500"
          >
            {Object.entries(registry.networks).map(([id, n]) => (
              <option key={id} value={id}>
                {n.label} · {n.feed_count} feeds
              </option>
            ))}
          </select>
          <svg
            className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M5.3 7.3a1 1 0 011.4 0L10 10.6l3.3-3.3a1 1 0 111.4 1.4l-4 4a1 1 0 01-1.4 0l-4-4a1 1 0 010-1.4z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <p className="mt-1.5 font-mono text-[11px] text-slate-500">chain_id: {net?.chain_id}</p>
      </div>

      <div className="border-b border-ink-700 p-4 pb-3">
        <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          Feed Catalog
        </label>
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <circle cx="9" cy="9" r="6" />
            <path d="M13.5 13.5 17 17" strokeLinecap="round" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && matches[0]) {
                onChange({ feed: matches[0][0] })
                onFeedPick?.()
              }
            }}
            placeholder="Search BTC, XAU, EUR, AAPL, 0x…"
            className="w-full rounded-lg border border-ink-600 bg-ink-800 py-2.5 pl-9 pr-3 text-sm text-slate-200 outline-none transition-colors placeholder:text-slate-600 hover:border-accent-500/40 focus:border-accent-500"
          />
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {['All', ...feedTypes].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${
                typeFilter === t
                  ? 'bg-accent-500 text-white'
                  : 'bg-ink-800 text-slate-400 hover:bg-ink-700 hover:text-slate-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <p className="mt-2 font-mono text-[11px] text-slate-500">
          {matches.length} of {net?.feed_count ?? 0} feeds
          {matches.length > MAX_VISIBLE ? ` · displaying top ${MAX_VISIBLE} by popularity` : ''}
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {visible.map(([slug, feed]) => {
          const selected = state.feed === slug
          return (
            <button
              key={slug}
              onClick={() => {
                onChange({ feed: slug })
                onFeedPick?.()
              }}
              className={`mb-1 flex w-full items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition-all ${
                selected
                  ? 'border-accent-500 bg-accent-500/10'
                  : 'border-transparent hover:border-ink-600 hover:bg-ink-800'
              }`}
            >
              <span className="w-6 shrink-0 text-center text-base">
                {TYPE_EMOJI[feed.feed_type] ?? '📊'}
              </span>
              <span className="min-w-0 flex-1">
                <span
                  className={`block truncate text-[13px] font-semibold ${
                    selected ? 'text-accent-300' : 'text-slate-200'
                  }`}
                >
                  {feed.name}
                </span>
                <span className="block truncate text-[10px] text-slate-500">
                  {feed.feed_type}
                  {feed.heartbeat ? ` · ♥ ${feed.heartbeat}s` : ''}
                  {feed.deviation_threshold_pct ? ` · ±${feed.deviation_threshold_pct}%` : ''}
                </span>
              </span>
              <span
                className={`shrink-0 text-[9px] font-bold uppercase tracking-wider ${
                  CATEGORY_STYLE[feed.category] ?? 'text-slate-500'
                }`}
              >
                {feed.category}
              </span>
            </button>
          )
        })}
        {visible.length === 0 && (
          <p className="p-4 text-center text-[12px] text-slate-500">
            No feeds match “{search}” on {net?.label}. Try another network — coverage differs per
            chain.
          </p>
        )}
      </div>

      <div className="border-t border-ink-700 p-3">
        <p className="text-[11px] leading-relaxed text-slate-500">
          <span className="font-semibold text-slate-400">Zero interaction walls.</span> Catalog
          sourced from Chainlink's reference-data directory. Every query is a stateless read-only
          call against public RPCs.
        </p>
      </div>
    </aside>
  )
}
