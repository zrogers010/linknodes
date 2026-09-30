import { useEffect, useState } from 'react'
import type { CompareResponse, QueryResult, Registry, SandboxState } from '../types'
import { ComparePanel } from './ComparePanel'
import { CopyButton } from './CopyButton'
import { JsonViewer } from './JsonViewer'
import { shareUrl } from '../hooks/useUrlState'

interface Props {
  registry: Registry
  state: SandboxState
  roundId: string
  onRoundIdChange: (v: string) => void
  result: QueryResult | null
  error: string | null
  loading: boolean
  latencyMs: number | null
  onSend: () => void
}

function truncateAddress(addr: string): string {
  return addr.length > 14 ? `${addr.slice(0, 8)}…${addr.slice(-6)}` : addr
}

function formatDuration(s: number): string {
  if (s < 120) return `${s}s`
  if (s < 7200) return `${Math.round(s / 60)}m`
  return `${Math.round(s / 3600)}h`
}

function formatPrice(price: number, feedName: string): string {
  const formatted = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: Math.abs(price) >= 100 ? 2 : Math.abs(price) >= 1 ? 4 : 8,
  }).format(price)
  return feedName.endsWith('/ USD') ? `$${formatted}` : formatted
}

function Chip({ label, value, copyText, href }: { label: string; value: string; copyText?: string; href?: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-ink-600 bg-ink-800 py-1 pl-3 pr-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer" className="font-mono text-[11px] text-accent-300 hover:underline">
          {value}
        </a>
      ) : (
        <span className="font-mono text-[11px] text-slate-300">{value}</span>
      )}
      {copyText ? <CopyButton text={copyText} /> : <span className="w-1" />}
    </div>
  )
}

export function Terminal({
  registry,
  state,
  roundId,
  onRoundIdChange,
  result,
  error,
  loading,
  latencyMs,
  onSend,
}: Props) {
  const feed = registry.networks[state.network]?.feeds[state.feed]
  const networkLabel = registry.networks[state.network]?.label ?? state.network
  const endpoint = `/v1/query/${state.network}/${state.feed}${roundId ? `?round_id=${roundId}` : ''}`

  const deployedChains = Object.values(registry.networks).filter((n) => state.feed in n.feeds).length
  const [compare, setCompare] = useState<CompareResponse | null>(null)
  const [comparing, setComparing] = useState(false)

  useEffect(() => setCompare(null), [state.feed])

  const runCompare = async () => {
    setComparing(true)
    try {
      const resp = await fetch(`/v1/compare/${state.feed}`)
      if (resp.ok) setCompare(await resp.json())
    } finally {
      setComparing(false)
    }
  }
  const updatedAt = result?.payload?.unix_timestamp as number | undefined
  const staleness = result ? Number(result.payload.staleness_seconds) : null
  const heartbeat = result?.meta.heartbeat_seconds != null ? Number(result.meta.heartbeat_seconds) : null
  const isFresh = staleness != null && (heartbeat == null || staleness <= heartbeat * 1.2)

  return (
    <section className="flex min-w-0 flex-col gap-4 bg-ink-950 p-4 sm:p-5 lg:h-full lg:overflow-y-auto">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <div className="flex w-full min-w-0 items-center gap-2 rounded-lg border border-ink-600 bg-ink-900 px-3 py-2.5 font-mono text-[12px] sm:text-[13px] lg:w-auto lg:flex-1">
          <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[11px] font-bold text-emerald-400">GET</span>
          <span className="truncate text-slate-300">{endpoint}</span>
          <CopyButton text={endpoint} className="ml-auto shrink-0" />
        </div>
        <input
          value={roundId}
          onChange={(e) => onRoundIdChange(e.target.value.replace(/[^0-9]/g, ''))}
          onKeyDown={(e) => e.key === 'Enter' && !loading && onSend()}
          placeholder="round_id (optional)"
          title="Query a historical round via getRoundData(); leave empty for the latest round"
          className="min-w-0 flex-1 rounded-lg border border-ink-600 bg-ink-900 px-3 py-2.5 font-mono text-[12px] text-slate-200 outline-none transition-colors placeholder:text-slate-600 focus:border-accent-500 sm:w-44 sm:flex-none"
        />
        <button
          onClick={onSend}
          disabled={loading}
          className={`shrink-0 rounded-lg bg-accent-500 px-6 py-2.5 text-[14px] font-bold tracking-wide text-white shadow-xl shadow-accent-500/30 transition-all hover:bg-accent-400 active:scale-[0.98] disabled:cursor-wait disabled:opacity-70 sm:px-8 sm:py-3 sm:text-[15px] ${
            loading ? '' : 'send-pulse'
          }`}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
                <path d="M22 12a10 10 0 00-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
              QUERYING…
            </span>
          ) : (
            'SEND REQUEST'
          )}
        </button>
      </div>

      {result && (
        <div
          className={`flex flex-wrap items-end justify-between gap-x-6 gap-y-2 rounded-xl border border-ink-700 bg-ink-900 px-5 py-4 transition-opacity ${
            loading ? 'opacity-50' : ''
          }`}
        >
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
              {String(result.meta.feed_name)} · {networkLabel}
              {result.query_type === 'historical_round' && ' · historical'}
            </p>
            <p className="mt-1 font-mono text-3xl font-bold tracking-tight text-white sm:text-4xl">
              {formatPrice(Number(result.payload.price), String(result.meta.feed_name))}
            </p>
          </div>
          {staleness != null && (
            <div className="flex items-center gap-2 pb-1 text-[12px] text-slate-400">
              <span
                className={`h-2 w-2 rounded-full ${
                  isFresh ? 'bg-emerald-400 shadow-[0_0_6px] shadow-emerald-400' : 'bg-amber-400 shadow-[0_0_6px] shadow-amber-400'
                }`}
              />
              updated {formatDuration(staleness)} ago
              {!isFresh && <span className="text-amber-400">(past heartbeat — market likely closed)</span>}
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="flex flex-wrap gap-2">
          {deployedChains > 1 && !compare && (
            <button
              onClick={runCompare}
              disabled={comparing}
              className="flex items-center gap-1.5 rounded-full border border-accent-500/40 bg-accent-500/10 py-1 pl-3 pr-3 text-[11px] font-semibold text-accent-300 transition-colors hover:bg-accent-500/20 disabled:cursor-wait disabled:opacity-60"
            >
              {comparing ? (
                <>
                  <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
                    <path d="M22 12a10 10 0 00-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  comparing…
                </>
              ) : (
                <>⇄ Compare on {deployedChains} chains</>
              )}
            </button>
          )}
          <Chip
            label="Contract"
            value={truncateAddress(String(result.meta.contract_address))}
            copyText={String(result.meta.contract_address)}
            href={String(result.meta.explorer_url)}
          />
          <Chip label="Decimals" value={String(result.meta.decimals)} />
          {heartbeat != null && <Chip label="Heartbeat" value={formatDuration(heartbeat)} />}
          {result.meta.deviation_threshold_pct != null && (
            <Chip label="Deviation" value={`±${result.meta.deviation_threshold_pct}%`} />
          )}
          {result.meta.risk_category != null && <Chip label="Risk" value={String(result.meta.risk_category)} />}
          {updatedAt !== undefined && (
            <Chip
              label="Updated"
              value={`${updatedAt} · ${new Date(updatedAt * 1000).toLocaleTimeString()}`}
              copyText={String(updatedAt)}
            />
          )}
        </div>
      )}

      {compare && (
        <ComparePanel data={compare} feedName={feed?.name ?? state.feed} onClose={() => setCompare(null)} />
      )}

      <div className="relative flex min-h-[320px] flex-col overflow-hidden rounded-xl border border-ink-700 bg-ink-900 shadow-2xl lg:min-h-0 lg:flex-1">
        <div className="flex items-center gap-2 border-b border-ink-700 bg-ink-850 px-4 py-2.5">
          <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
          <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
          <span className="h-3 w-3 rounded-full bg-[#28c840]" />
          <span className="ml-3 hidden font-mono text-[11px] text-slate-500 sm:inline">
            response — {feed?.name ?? state.feed} on {state.network}
            {roundId ? ` · round ${roundId}` : ''}
          </span>
          <span className="ml-auto flex items-center gap-3">
            {result && !error && <span className="font-mono text-[11px] font-semibold text-emerald-400">200 OK</span>}
            {error && <span className="font-mono text-[11px] font-semibold text-rose-400">ERROR</span>}
            {latencyMs !== null && <span className="font-mono text-[11px] text-slate-500">{latencyMs} ms</span>}
            {result && <CopyButton text={JSON.stringify(result, null, 2)} />}
          </span>
        </div>

        <div className="min-h-0 flex-1 overflow-auto p-4">
          {loading && !result && (
            <p className="font-mono text-[12.5px] text-slate-500">→ dispatching read-only eth_call to public RPC…</p>
          )}
          {!loading && !result && !error && (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <div className="text-4xl">📡</div>
              <p className="max-w-sm text-sm text-slate-500">
                Pick any of the {registry.networks[state.network]?.feed_count ?? 0} feeds on{' '}
                {networkLabel} — the live on-chain round loads automatically.
              </p>
            </div>
          )}
          {error && (
            <pre className="whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-rose-300">{error}</pre>
          )}
          {result && <JsonViewer data={result} />}
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-900 px-3 py-2">
        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Share</span>
        <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-400">{shareUrl(state)}</span>
        <CopyButton text={shareUrl(state)} />
      </div>
    </section>
  )
}
