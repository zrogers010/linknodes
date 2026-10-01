import { useCallback, useEffect, useRef, useState } from 'react'
import { apiUrl } from '../config'
import { ControlPanel } from '../components/ControlPanel'
import { SnippetColumn } from '../components/SnippetColumn'
import { Terminal } from '../components/Terminal'
import { useUrlState } from '../hooks/useUrlState'
import type { QueryResult, Registry } from '../types'

export function SandboxPage({ registry }: { registry: Registry }) {
  const [state, updateState] = useUrlState()
  const [roundId, setRoundId] = useState('')
  const [result, setResult] = useState<QueryResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)

  const [pickerOpen, setPickerOpen] = useState(false)
  const [snippetsOpen, setSnippetsOpen] = useState(false)

  // Monotonic sequence so a slow response never overwrites a newer one.
  const requestSeq = useRef(0)

  const sendRequest = useCallback(async (network: string, feed: string, rid: string) => {
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    const started = performance.now()
    try {
      const qs = rid ? `?round_id=${rid}` : ''
      const resp = await fetch(apiUrl(`/v1/query/${network}/${feed}${qs}`))
      const body = await resp.json()
      if (seq !== requestSeq.current) return
      setLatencyMs(Math.round(performance.now() - started))
      if (!resp.ok) {
        setResult(null)
        setError(JSON.stringify(body, null, 2))
      } else {
        setResult(body)
      }
    } catch (e) {
      if (seq !== requestSeq.current) return
      setLatencyMs(Math.round(performance.now() - started))
      setResult(null)
      setError(String(e))
    } finally {
      if (seq === requestSeq.current) setLoading(false)
    }
  }, [])

  // Auto-query whenever the route changes -- covers first load, shared links,
  // and every selection in the picker. Round IDs are feed-specific, so reset.
  useEffect(() => {
    setRoundId('')
    sendRequest(state.network, state.feed, '')
  }, [state.network, state.feed, sendRequest])

  const feedName = registry.networks[state.network]?.feeds[state.feed]?.name ?? state.feed
  const networkLabel = registry.networks[state.network]?.label ?? state.network

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto lg:grid lg:grid-cols-[320px_minmax(0,1fr)_340px] lg:overflow-hidden">
      {/* Mobile route bar: shows the current selection, opens the picker */}
      <button
        onClick={() => setPickerOpen(true)}
        className="flex items-center gap-2 border-b border-ink-700 bg-ink-900 px-4 py-3 text-left lg:hidden"
      >
        <span className="rounded-md bg-ink-800 px-2 py-1 font-mono text-[11px] text-slate-400">
          {networkLabel}
        </span>
        <span className="min-w-0 flex-1 truncate text-[14px] font-semibold text-slate-100">
          {feedName}
        </span>
        <span className="flex items-center gap-1 rounded-lg bg-accent-500/15 px-2.5 py-1.5 text-[12px] font-semibold text-accent-300">
          Change
          <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M5.3 7.3a1 1 0 011.4 0L10 10.6l3.3-3.3a1 1 0 111.4 1.4l-4 4a1 1 0 01-1.4 0l-4-4a1 1 0 010-1.4z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      </button>

      {/* Feed picker: drawer on mobile, first grid column on desktop */}
      <div
        className={`${
          pickerOpen ? 'fixed inset-0 z-40 flex flex-col bg-ink-950' : 'hidden'
        } lg:contents`}
      >
        <div className="flex items-center justify-between border-b border-ink-700 bg-ink-900 px-4 py-3 lg:hidden">
          <span className="text-[14px] font-bold text-slate-100">Select a feed</span>
          <button
            onClick={() => setPickerOpen(false)}
            className="rounded-lg bg-ink-800 px-3 py-1.5 text-[13px] font-semibold text-slate-300 transition-colors hover:bg-ink-700"
          >
            Close
          </button>
        </div>
        <div className="min-h-0 flex-1 lg:contents">
          <ControlPanel
            registry={registry}
            state={state}
            onChange={updateState}
            onFeedPick={() => setPickerOpen(false)}
          />
        </div>
      </div>

      <Terminal
        registry={registry}
        state={state}
        roundId={roundId}
        onRoundIdChange={setRoundId}
        result={result}
        error={error}
        loading={loading}
        latencyMs={latencyMs}
        onSend={() => sendRequest(state.network, state.feed, roundId)}
      />

      {/* Snippets: third column on desktop, collapsible section on mobile */}
      <div className="hidden h-full min-h-0 lg:block">
        <SnippetColumn registry={registry} state={state} />
      </div>
      <div className="border-t border-ink-700 lg:hidden">
        <button
          onClick={() => setSnippetsOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3.5"
        >
          <span className="text-[13px] font-semibold text-slate-200">Integration snippets</span>
          <svg
            className={`h-4 w-4 text-slate-500 transition-transform ${snippetsOpen ? 'rotate-180' : ''}`}
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M5.3 7.3a1 1 0 011.4 0L10 10.6l3.3-3.3a1 1 0 111.4 1.4l-4 4a1 1 0 01-1.4 0l-4-4a1 1 0 010-1.4z"
              clipRule="evenodd"
            />
          </svg>
        </button>
        {snippetsOpen && (
          <div className="h-[480px]">
            <SnippetColumn registry={registry} state={state} />
          </div>
        )}
      </div>
    </div>
  )
}
