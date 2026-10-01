import { useEffect, useMemo, useState } from 'react'
import { apiUrl } from '../config'

interface Operator {
  id: string
  name: string
  type: string
  region: string
  since: number
  website: string
  services: string[]
  description: string
}

interface OperatorsResponse {
  disclaimer: string
  operators: Operator[]
}

type SortKey = 'since' | 'name'

const TYPE_LABEL: Record<string, string> = {
  independent: 'Independent',
  'staking-provider': 'Staking Provider',
  telecom: 'Telecom',
  enterprise: 'Enterprise',
}

const TYPE_STYLE: Record<string, string> = {
  independent: 'border-sky-500/40 bg-sky-500/10 text-sky-400',
  'staking-provider': 'border-violet-500/40 bg-violet-500/10 text-violet-400',
  telecom: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
  enterprise: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
}

export function OperatorsPage() {
  const [data, setData] = useState<OperatorsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState('All')
  const [sortKey, setSortKey] = useState<SortKey>('since')

  useEffect(() => {
    fetch(apiUrl('/v1/operators'))
      .then((r) => {
        if (!r.ok) throw new Error(`operators fetch failed: HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [])

  const types = useMemo(() => {
    if (!data) return []
    return [...new Set(data.operators.map((o) => o.type))]
  }, [data])

  const visible = useMemo(() => {
    if (!data) return []
    const filtered = data.operators.filter((o) => typeFilter === 'All' || o.type === typeFilter)
    return filtered.sort((a, b) =>
      sortKey === 'since' ? a.since - b.since || a.name.localeCompare(b.name) : a.name.localeCompare(b.name),
    )
  }, [data, typeFilter, sortKey])

  if (error) {
    return (
      <main className="flex min-h-0 flex-1 items-center justify-center">
        <p className="font-mono text-sm text-rose-400">{error}</p>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="flex min-h-0 flex-1 items-center justify-center">
        <p className="font-mono text-sm text-slate-500">loading operators…</p>
      </main>
    )
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-1 flex items-baseline gap-3">
          <h2 className="text-xl font-bold text-white">Node Operators</h2>
          <span className="font-mono text-[12px] text-slate-500">{data.operators.length} listed</span>
        </div>
        <p className="mb-5 max-w-3xl text-[13px] leading-relaxed text-slate-500">{data.disclaimer}</p>

        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="flex flex-wrap gap-1">
            {['All', ...types].map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`rounded-full px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                  typeFilter === t
                    ? 'bg-accent-500 text-white'
                    : 'bg-ink-800 text-slate-400 hover:bg-ink-700 hover:text-slate-200'
                }`}
              >
                {TYPE_LABEL[t] ?? t}
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
              <option value="since">Operating since (veterans first)</option>
              <option value="name">Name A–Z</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {visible.map((op) => (
            <div
              key={op.id}
              className="flex flex-col rounded-xl border border-ink-700 bg-ink-900 p-4 transition-colors hover:border-ink-600"
            >
              <div className="mb-2 flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ink-800 font-mono text-[13px] font-black text-accent-300">
                  {op.name.slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-[14px] font-bold text-slate-100">{op.name}</h3>
                  <p className="text-[11px] text-slate-500">
                    {op.region} · since {op.since}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                    TYPE_STYLE[op.type] ?? 'border-ink-600 text-slate-500'
                  }`}
                >
                  {TYPE_LABEL[op.type] ?? op.type}
                </span>
              </div>

              <p className="mb-3 text-[12px] leading-relaxed text-slate-400">{op.description}</p>

              <div className="mt-auto flex items-center gap-1.5">
                {op.services.map((s) => (
                  <span
                    key={s}
                    className="rounded-md bg-ink-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-400"
                  >
                    {s}
                  </span>
                ))}
                <a
                  href={op.website}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-auto text-[11px] font-medium text-accent-300 hover:underline"
                >
                  {op.website.replace(/^https?:\/\/(www\.)?/, '')} ↗
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}
