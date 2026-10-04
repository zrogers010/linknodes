import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { comparePopularity } from '../popularity'
import { SEO } from '../components/SEO'
import type { Registry } from '../types'

type SortKey = 'popularity' | 'coverage' | 'name' | 'heartbeat'

const TYPE_EMOJI: Record<string, string> = {
  Crypto: '🪙',
  Forex: '💱',
  Commodities: '🛢️',
  Equities: '📈',
  Fiat: '💵',
  Macroeconomics: '🏛️',
}

const CATEGORY_STYLE: Record<string, string> = {
  low: 'border-emerald-500/40 text-emerald-400',
  medium: 'border-amber-500/40 text-amber-400',
  high: 'border-rose-500/40 text-rose-400',
  new: 'border-sky-500/40 text-sky-400',
  custom: 'border-violet-500/40 text-violet-400',
  unranked: 'border-ink-600 text-slate-500',
}

interface AggregatedFeed {
  slug: string
  name: string
  feedType: string
  assetName: string
  chains: { key: string; label: string }[]
  minHeartbeat: number | null
  minDeviation: number | null
  /** Best (lowest-risk) category seen across deployments. */
  category: string
}

const CATEGORY_RANK = ['low', 'medium', 'high', 'new', 'custom', 'unranked']

function aggregate(registry: Registry): AggregatedFeed[] {
  const bySlug = new Map<string, AggregatedFeed>()
  for (const [netKey, net] of Object.entries(registry.networks)) {
    for (const [slug, feed] of Object.entries(net.feeds)) {
      let agg = bySlug.get(slug)
      if (!agg) {
        agg = {
          slug,
          name: feed.name,
          feedType: feed.feed_type,
          assetName: feed.asset_name,
          chains: [],
          minHeartbeat: null,
          minDeviation: null,
          category: feed.category,
        }
        bySlug.set(slug, agg)
      }
      agg.chains.push({ key: netKey, label: net.label })
      if (feed.heartbeat != null) {
        agg.minHeartbeat = agg.minHeartbeat == null ? feed.heartbeat : Math.min(agg.minHeartbeat, feed.heartbeat)
      }
      if (feed.deviation_threshold_pct != null) {
        agg.minDeviation =
          agg.minDeviation == null ? feed.deviation_threshold_pct : Math.min(agg.minDeviation, feed.deviation_threshold_pct)
      }
      if (CATEGORY_RANK.indexOf(feed.category) < CATEGORY_RANK.indexOf(agg.category)) {
        agg.category = feed.category
      }
    }
  }
  return [...bySlug.values()]
}

/** "btc-usd-shared-svr" -> "shared svr"; canonical two-part slugs return ''. */
function variantSuffix(slug: string): string {
  return slug.split('-').slice(2).join(' ')
}

function formatHeartbeat(s: number | null): string {
  if (s == null) return '—'
  if (s < 120) return `${s}s`
  if (s < 7200) return `${Math.round(s / 60)}m`
  return `${Math.round(s / 3600)}h`
}

export function FeedsPage({ registry }: { registry: Registry }) {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [sortKey, setSortKey] = useState<SortKey>('popularity')

  const allFeeds = useMemo(() => aggregate(registry), [registry])

  const feedTypes = useMemo(() => {
    const counts = new Map<string, number>()
    for (const f of allFeeds) counts.set(f.feedType, (counts.get(f.feedType) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t)
  }, [allFeeds])

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    const filtered = allFeeds.filter((f) => {
      if (typeFilter !== 'All' && f.feedType !== typeFilter) return false
      if (!q) return true
      return f.slug.includes(q) || f.name.toLowerCase().includes(q) || f.assetName.toLowerCase().includes(q)
    })
    return filtered.sort((a, b) => {
      if (sortKey === 'popularity') {
        return comparePopularity(
          { slug: a.slug, chainCount: a.chains.length, name: a.name },
          { slug: b.slug, chainCount: b.chains.length, name: b.name },
        )
      }
      if (sortKey === 'coverage') {
        return b.chains.length - a.chains.length || a.name.localeCompare(b.name)
      }
      if (sortKey === 'heartbeat') {
        return (a.minHeartbeat ?? Infinity) - (b.minHeartbeat ?? Infinity) || a.name.localeCompare(b.name)
      }
      return a.name.localeCompare(b.name)
    })
  }, [allFeeds, search, typeFilter, sortKey])

  return (
    <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
      <SEO 
        title="Feed Catalog — 1,400+ Chainlink Data Feeds"
        description="Complete catalog of Chainlink Data Feeds aggregated across 13 mainnets. Browse crypto, forex, equities, commodities, and macro feeds by coverage, heartbeat, and risk rating."
        path="/feeds"
      />
      <div className="mx-auto max-w-7xl">
        <div className="mb-1 flex items-baseline gap-3">
          <h2 className="text-xl font-bold text-white">Feed Catalog</h2>
          <span className="font-mono text-[12px] text-slate-500">
            {allFeeds.length} unique feeds · {Object.keys(registry.networks).length} chains
          </span>
        </div>
        <p className="mb-5 max-w-2xl text-[13px] text-slate-500">
          Every Chainlink Data Feed, aggregated across chains. Chainlink publishes no per-feed
          query counts, so popularity blends a curated mainstream-asset ranking with chain
          coverage — the feeds protocols actually integrate float to the top.
        </p>

        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="relative w-full sm:w-auto">
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
              placeholder="Search feeds…"
              className="w-full rounded-lg border border-ink-600 bg-ink-800 py-2 pl-9 pr-3 text-sm text-slate-200 outline-none transition-colors placeholder:text-slate-600 focus:border-accent-500 sm:w-64"
            />
          </div>
          <div className="flex flex-wrap gap-1">
            {['All', ...feedTypes].map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`rounded-full px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                  typeFilter === t
                    ? 'bg-accent-500 text-white'
                    : 'bg-ink-800 text-slate-400 hover:bg-ink-700 hover:text-slate-200'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Sort by</span>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="appearance-none rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-[13px] font-medium text-slate-200 outline-none focus:border-accent-500"
            >
              <option value="popularity">Popularity (mainstream first)</option>
              <option value="coverage">Chain coverage</option>
              <option value="heartbeat">Fastest heartbeat</option>
              <option value="name">Name A–Z</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {visible.map((f) => (
            <div
              key={f.slug}
              className="flex flex-col rounded-xl border border-ink-700 bg-ink-900 p-4 transition-colors hover:border-ink-600"
            >
              <div className="mb-2 flex items-start gap-2.5">
                <span className="text-xl leading-none">{TYPE_EMOJI[f.feedType] ?? '📊'}</span>
                <div className="min-w-0 flex-1">
                  <h3 className="flex items-center gap-1.5 truncate text-[14px] font-bold text-slate-100">
                    {f.name}
                    {variantSuffix(f.slug) && (
                      <span className="rounded bg-ink-700 px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                        {variantSuffix(f.slug)}
                      </span>
                    )}
                  </h3>
                  <p className="truncate text-[11px] text-slate-500">
                    {f.assetName || f.feedType}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                    CATEGORY_STYLE[f.category] ?? CATEGORY_STYLE.unranked
                  }`}
                >
                  {f.category}
                </span>
              </div>

              <div className="mb-3 flex gap-4 font-mono text-[11px] text-slate-400">
                <span title="Deployed chains">
                  <span className="text-slate-600">chains</span>{' '}
                  <span className="font-bold text-accent-300">{f.chains.length}</span>
                </span>
                <span title="Fastest heartbeat across deployments">
                  <span className="text-slate-600">♥</span> {formatHeartbeat(f.minHeartbeat)}
                </span>
                {f.minDeviation != null && (
                  <span title="Tightest deviation threshold across deployments">
                    <span className="text-slate-600">dev</span> ±{f.minDeviation}%
                  </span>
                )}
              </div>

              <div className="mt-auto flex flex-wrap gap-1">
                {f.chains.map((c) => (
                  <Link
                    key={c.key}
                    to={`/products/data-feeds?chain=${c.key}&feed=${f.slug}`}
                    title={`Query ${f.name} on ${c.label} in the sandbox`}
                    className="rounded-md bg-ink-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-400 transition-colors hover:bg-accent-500 hover:text-white"
                  >
                    {c.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>

        {visible.length === 0 && (
          <p className="py-16 text-center text-sm text-slate-500">No feeds match your filters.</p>
        )}
      </div>
    </main>
  )
}
