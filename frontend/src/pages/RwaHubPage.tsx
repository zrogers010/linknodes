import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageLayout } from '../components/PageLayout'
import { SEO } from '../components/SEO'
import { BuildingBankIcon, CalendarIcon, ChevronRightIcon, ExternalLinkIcon, InfoCircleIcon } from '../components/icons/Icon'
import { apiUrl } from '../config'
import {
  SESSION_LABEL,
  SESSION_STYLE,
  displaySession,
  formatLastUpdateEt,
  type MarketSession,
} from '../marketHours'
import type { FeedMeta, Freshness, QueryResult, Registry, Stream247, Streams247Doc } from '../types'

type AssetClass = 'stock' | 'commodity' | 'tokenized'

interface HubRow {
  slug: string
  chain: string
  chainLabel: string
  assetClass: AssetClass
  feed: FeedMeta
}

const FEATURED_TSLA = { chain: 'arbitrum', slug: 'tsla-usd' }

function classifyAsset(feed: FeedMeta): AssetClass | null {
  const type = (feed.feed_type || '').toLowerCase()
  const hours = (feed.market_hours || '').toLowerCase()
  const name = feed.name || ''
  const product = (feed.product_type || '').toLowerCase()
  const base = (feed.base || '').toLowerCase()

  if (type.includes('macro') || product === 'blockchain') return null
  if (
    type.includes('tokenized') ||
    /tGLD|tokenized|ondo/i.test(name) ||
    /on$/i.test(base) ||
    product === 'navlink'
  ) {
    return 'tokenized'
  }
  if (type.includes('commodit') || hours === 'precious_metals' || hours === 'wti') {
    return 'commodity'
  }
  if (
    type.includes('equit') ||
    type === 'stocks' ||
    hours === 'nyse' ||
    hours === 'us_equities_24/5' ||
    hours === 'lse' ||
    hours === 'euronext_milan'
  ) {
    return 'stock'
  }
  return null
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: Math.abs(price) >= 100 ? 2 : Math.abs(price) >= 1 ? 4 : 6,
  }).format(price)
}

function SessionBadge({ session }: { session: MarketSession }) {
  return (
    <span className={`inline-flex border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${SESSION_STYLE[session]}`}>
      {SESSION_LABEL[session]}
    </span>
  )
}

export function RwaHubPage({ registry }: { registry: Registry }) {
  const [streamsDoc, setStreamsDoc] = useState<Streams247Doc | null>(null)
  const [chainFilter, setChainFilter] = useState<string>('all')
  const [classFilter, setClassFilter] = useState<string>('all')
  const [prices, setPrices] = useState<Record<string, { price: number; freshness: Freshness | null; updatedAt: number | null }>>({})
  const pricesRef = useRef(prices)
  const [nowMs, setNowMs] = useState(() => Date.now())

  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 30_000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    fetch(apiUrl('/v1/streams-247'))
      .then((r) => (r.ok ? r.json() : null))
      .then((doc) => {
        if (doc) setStreamsDoc(doc)
      })
      .catch(() => {
        /* hub still lists on-chain feeds */
      })
  }, [])

  const rows = useMemo(() => {
    const out: HubRow[] = []
    for (const [chain, net] of Object.entries(registry.networks)) {
      for (const [slug, feed] of Object.entries(net.feeds)) {
        const assetClass = classifyAsset(feed)
        if (!assetClass) continue
        out.push({ slug, chain, chainLabel: net.label, assetClass, feed })
      }
    }
    out.sort((a, b) => a.feed.name.localeCompare(b.feed.name) || a.chainLabel.localeCompare(b.chainLabel))
    return out
  }, [registry])

  const chains = useMemo(() => {
    const set = new Map<string, string>()
    for (const row of rows) set.set(row.chain, row.chainLabel)
    return [...set.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [rows])

  const visible = useMemo(() => {
    return rows.filter((row) => {
      if (chainFilter !== 'all' && row.chain !== chainFilter) return false
      if (classFilter !== 'all' && row.assetClass !== classFilter) return false
      return true
    })
  }, [rows, chainFilter, classFilter])

  useEffect(() => {
    let cancelled = false
    const featuredKey = `${FEATURED_TSLA.chain}/${FEATURED_TSLA.slug}`
    const keys = visible.map((row) => `${row.chain}/${row.slug}`)
    const unique = [...new Set([featuredKey, ...keys])].slice(0, 25)

    const run = async () => {
      const pending = unique.filter((key) => !(key in pricesRef.current))
      const batchSize = 2
      for (let i = 0; i < pending.length; i += batchSize) {
        if (cancelled) return
        const batch = pending.slice(i, i + batchSize)
        const results = await Promise.all(
          batch.map(async (key) => {
            const [chain, slug] = key.split('/')
            try {
              const r = await fetch(apiUrl(`/v1/query/${chain}/${slug}`))
              if (!r.ok) return [key, null] as const
              const json = (await r.json()) as QueryResult
              const freshness = (json.meta.freshness as Freshness | undefined) ?? null
              return [key, {
                price: Number(json.payload.price),
                freshness,
                updatedAt: Number(json.payload.unix_timestamp) || null,
              }] as const
            } catch {
              return [key, null] as const
            }
          }),
        )
        if (cancelled) return
        setPrices((prev) => {
          const next = { ...prev }
          for (const [key, value] of results) {
            if (value) next[key] = value
          }
          pricesRef.current = next
          return next
        })
        await new Promise((resolve) => window.setTimeout(resolve, 350))
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [visible])

  const tsla = registry.networks[FEATURED_TSLA.chain]?.feeds[FEATURED_TSLA.slug]
  const tslaPrice = prices[`${FEATURED_TSLA.chain}/${FEATURED_TSLA.slug}`]
  const tslaStream = streamsDoc?.streams.find((s) => s.base === 'TSLA')
  const cash = displaySession(nowMs, false)
  const streams = streamsDoc?.streams ?? []

  const freshnessLine = (row: HubRow) => {
    const hit = prices[`${row.chain}/${row.slug}`]
    if (!hit) return 'Loading last update…'
    if (hit.freshness?.status === 'market_closed') return hit.freshness.message
    if (hit.updatedAt) return `Last update ${formatLastUpdateEt(hit.updatedAt)}`
    return hit.freshness?.message ?? ''
  }

  return (
    <PageLayout>
      <SEO
        title="RWA and Chainlink 24/7 feeds"
        description="Live stock, commodity, and tokenized-asset Chainlink Data Feeds by chain, plus the 17 Arbitrum 24/7 Data Streams. Session badges are calculated by LinkNodes, not an oracle value."
        path="/rwa"
      />

      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <div className="mb-2 inline-flex items-center gap-1.5 border border-ink-600 bg-ink-800 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              <BuildingBankIcon size={12} />
              Real-world assets
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Stocks, commodities, and Chainlink 24/7
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              On-chain Data Feeds for equities, commodities, and tokenized assets, with live prices from the same reads as the sandbox.
              Chainlink 24/7 Data Streams are listed separately — they have no proxy address and are not queried here.
            </p>
          </div>
          <Link
            to="/chainlink-247"
            className="inline-flex items-center gap-1.5 border border-ink-600 bg-ink-800 px-3 py-2 text-xs font-medium text-slate-200 hover:border-ink-500"
          >
            Chainlink 24/7 explained
            <ChevronRightIcon size={14} />
          </Link>
        </div>

        <div className="mb-6 border border-ink-700 bg-ink-900 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <CalendarIcon size={16} className="text-accent-400" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">US cash session</span>
                <SessionBadge session={cash} />
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
                Calculated by LinkNodes from NYSE hours and US market holidays — not an oracle value and not Chainlink
                {' '}<code className="text-slate-400">marketStatus</code>.
                Open = Regular 9:30–4:00 PM ET. Pre / Post / Overnight follow the 24/5 window. Closed covers the weekend gap and holidays.
                Extended is the 24/7 weekend and holiday session.
              </p>
            </div>
          </div>
        </div>

        {tsla && (
          <section className="mb-8 border border-ink-700 bg-ink-900 p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-white">Featured example — TSLA/USD</h2>
              <SessionBadge session={displaySession(nowMs, false)} />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">On-chain Data Feed</p>
                <p className="mt-1 text-lg font-bold text-white">{tsla.name}</p>
                <p className="text-xs text-slate-400">Arbitrum One · NYSE hours · heartbeat {tsla.heartbeat}s</p>
                <p className="mt-2 font-mono text-2xl font-bold text-white">
                  {tslaPrice ? formatPrice(tslaPrice.price) : '—'}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {tslaPrice?.freshness?.status === 'market_closed'
                    ? tslaPrice.freshness.message
                    : tslaPrice?.updatedAt
                      ? `Last update ${formatLastUpdateEt(tslaPrice.updatedAt)}`
                      : 'Querying latestRoundData…'}
                </p>
                <Link
                  to={`/feeds/${FEATURED_TSLA.chain}/${FEATURED_TSLA.slug}`}
                  className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-accent-400 hover:text-accent-300"
                >
                  Open feed page
                  <ChevronRightIcon size={12} />
                </Link>
              </div>
              <div className="border border-ink-700 bg-ink-950 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">24/7 Stream (list only)</p>
                <p className="mt-1 text-sm font-bold text-white">{tslaStream?.display_name ?? 'TSLA/USD'}</p>
                <p className="mt-1 font-mono text-[11px] break-all text-slate-400">{tslaStream?.feed_id ?? '—'}</p>
                <p className="mt-2 text-xs leading-relaxed text-slate-500">
                  Schema {tslaStream?.schema ?? 'v2'} — price only, no marketStatus. No on-chain proxy.
                  Access goes through Chainlink; this is not a live quote from the closed NYSE.
                </p>
              </div>
            </div>
          </section>
        )}

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-400">
            Chain
            <select
              value={chainFilter}
              onChange={(e) => setChainFilter(e.target.value)}
              className="mt-1 block border border-ink-600 bg-ink-900 px-2 py-1.5 text-xs text-slate-200"
            >
              <option value="all">All chains</option>
              {chains.map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-400">
            Asset class
            <select
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              className="mt-1 block border border-ink-600 bg-ink-900 px-2 py-1.5 text-xs text-slate-200"
            >
              <option value="all">Stocks, commodities, tokenized</option>
              <option value="stock">Stocks</option>
              <option value="commodity">Commodities</option>
              <option value="tokenized">Tokenized assets</option>
            </select>
          </label>
          <p className="ml-auto text-[11px] text-slate-500">{visible.length} feeds</p>
        </div>

        <div className="mb-8 overflow-x-auto border border-ink-700">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-ink-900 text-[10px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-3 py-2 font-semibold">Feed</th>
                <th className="px-3 py-2 font-semibold">Chain</th>
                <th className="px-3 py-2 font-semibold">Class</th>
                <th className="px-3 py-2 font-semibold">Hours</th>
                <th className="px-3 py-2 font-semibold">Session</th>
                <th className="px-3 py-2 font-semibold">Price</th>
                <th className="px-3 py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => {
                const key = `${row.chain}/${row.slug}`
                const hit = prices[key]
                const session = displaySession(nowMs, Boolean(row.feed.is_247))
                return (
                  <tr key={key} className="border-t border-ink-700 bg-ink-950 hover:bg-ink-900">
                    <td className="px-3 py-2">
                      <Link to={`/feeds/${row.chain}/${row.slug}`} className="font-medium text-white hover:text-accent-300">
                        {row.feed.name}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-slate-400">{row.chainLabel}</td>
                    <td className="px-3 py-2 capitalize text-slate-400">{row.assetClass}</td>
                    <td className="px-3 py-2 text-slate-400">{row.feed.market_hours || '—'}</td>
                    <td className="px-3 py-2"><SessionBadge session={session} /></td>
                    <td className="px-3 py-2 font-mono text-slate-200">{hit ? formatPrice(hit.price) : '…'}</td>
                    <td className="px-3 py-2 text-slate-500">{freshnessLine(row)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <section className="border border-ink-700 bg-ink-900 p-5">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-bold text-white">24/7 Streams</h2>
            <span className="border border-ink-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {streams.length} on Arbitrum
            </span>
          </div>
          <div className="mb-4 flex gap-2 border border-ink-700 bg-ink-950 p-3 text-[12px] leading-relaxed text-slate-400">
            <InfoCircleIcon size={14} className="mt-0.5 shrink-0 text-slate-500" />
            <p>
              These 17 Data Streams come from Chainlink&apos;s reference-data directory. They use report schema v2 (price only, no marketStatus)
              and have no on-chain proxy. Access currently goes through Chainlink — contact them before integrating.
              Off-hours prices come from perpetual-futures venues and are not a live quote from the closed traditional exchange.
              On-chain 24/7 stock Data Feeds do not exist yet.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {streams.map((stream: Stream247) => (
              <article key={stream.feed_id} className="border border-ink-700 bg-ink-950 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-white">{stream.display_name}</h3>
                    <p className="text-[11px] text-slate-500">{stream.asset_name || stream.asset_class}</p>
                  </div>
                  <span className="shrink-0 border border-ink-600 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-slate-400">
                    {stream.asset_class}
                  </span>
                </div>
                <p className="mt-2 font-mono text-[10px] break-all text-slate-500">{stream.feed_id}</p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Schema {stream.schema} · chain {stream.chain_id} · list only
                </p>
              </article>
            ))}
          </div>
          <a
            href="https://docs.chain.link/data-feeds/tokenized-equity-feeds"
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex items-center gap-1 text-xs text-accent-400 hover:text-accent-300"
          >
            Tokenized equity docs (reach out before integrating)
            <ExternalLinkIcon size={12} />
          </a>
        </section>
      </div>
    </PageLayout>
  )
}
