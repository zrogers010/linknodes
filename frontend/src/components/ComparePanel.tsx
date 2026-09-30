import type { CompareResponse } from '../types'

function formatAgo(s: number): string {
  if (s < 120) return `${s}s ago`
  if (s < 7200) return `${Math.round(s / 60)}m ago`
  return `${Math.round(s / 3600)}h ago`
}

export function ComparePanel({
  data,
  feedName,
  onClose,
}: {
  data: CompareResponse
  feedName: string
  onClose: () => void
}) {
  const ok = data.results.filter((r) => r.success)
  const sorted = [...data.results].sort((a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity))
  const median = ok.length
    ? [...ok].sort((a, b) => a.price! - b.price!)[Math.floor(ok.length / 2)].price!
    : 0
  const minNet = data.summary.min?.network
  const maxNet = data.summary.max?.network

  return (
    <div className="overflow-hidden rounded-xl border border-ink-700 bg-ink-900">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-ink-700 bg-ink-850 px-4 py-2.5">
        <span className="text-[12px] font-bold text-slate-200">
          {feedName} across {data.summary.chains_ok}/{data.summary.chains_queried} chains
        </span>
        {data.summary.spread_bps != null && (
          <span className="font-mono text-[11px] text-slate-400">
            spread <span className="font-bold text-accent-300">{data.summary.spread_bps} bps</span>
          </span>
        )}
        <span className="font-mono text-[11px] text-slate-500">{Math.round(data.summary.total_latency_ms)} ms total</span>
        <button
          onClick={onClose}
          className="ml-auto rounded-md px-2 py-0.5 text-[11px] font-semibold text-slate-400 transition-colors hover:bg-ink-700 hover:text-slate-200"
        >
          Close ✕
        </button>
      </div>

      <div className="divide-y divide-ink-800">
        {sorted.map((r) => {
          const diffBps = r.success && median ? ((r.price! - median) / median) * 10000 : null
          return (
            <div key={r.network} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2">
              <span className="w-36 truncate text-[12px] font-semibold text-slate-300">{r.network_label}</span>
              {r.success ? (
                <>
                  <span
                    className={`font-mono text-[13px] font-bold ${
                      r.network === maxNet
                        ? 'text-emerald-400'
                        : r.network === minNet
                          ? 'text-rose-400'
                          : 'text-slate-200'
                    }`}
                  >
                    {new Intl.NumberFormat('en-US', {
                      maximumFractionDigits: Math.abs(r.price!) >= 100 ? 2 : Math.abs(r.price!) >= 1 ? 4 : 8,
                    }).format(r.price!)}
                  </span>
                  {diffBps != null && (
                    <span
                      className={`rounded-full px-1.5 py-0.5 font-mono text-[10px] ${
                        Math.abs(diffBps) < 1
                          ? 'bg-ink-800 text-slate-500'
                          : diffBps > 0
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-rose-500/10 text-rose-400'
                      }`}
                    >
                      {diffBps >= 0 ? '+' : ''}
                      {diffBps.toFixed(1)} bps
                    </span>
                  )}
                  <span className="ml-auto flex items-center gap-3 font-mono text-[10px] text-slate-500">
                    <span>{formatAgo(r.staleness_seconds!)}</span>
                    <span className="hidden sm:inline">{Math.round(r.rpc_latency_ms!)} ms rpc</span>
                    <a
                      href={r.explorer_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent-300 hover:underline"
                    >
                      contract ↗
                    </a>
                  </span>
                </>
              ) : (
                <span className="font-mono text-[11px] text-rose-400">{r.error}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
