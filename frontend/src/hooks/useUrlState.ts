import { useCallback, useEffect, useState } from 'react'
import type { SandboxState } from '../types'

const DEFAULTS: SandboxState = {
  network: 'ethereum',
  feed: 'btc-usd',
}

function readUrl(): SandboxState {
  const params = new URLSearchParams(window.location.search)
  return {
    network: params.get('chain') ?? DEFAULTS.network,
    feed: params.get('feed') ?? DEFAULTS.feed,
  }
}

/**
 * Two-way binding between sandbox selections and URL query params so any
 * console state is shareable as a plain link (?chain=arbitrum&feed=xau-usd).
 */
export function useUrlState(): [SandboxState, (patch: Partial<SandboxState>) => void] {
  const [state, setState] = useState<SandboxState>(readUrl)

  const update = useCallback((patch: Partial<SandboxState>) => {
    setState((prev) => {
      const next = { ...prev, ...patch }
      const params = new URLSearchParams()
      params.set('chain', next.network)
      params.set('feed', next.feed)
      window.history.replaceState(null, '', `${window.location.pathname}?${params}`)
      return next
    })
  }, [])

  useEffect(() => {
    const onPop = () => setState(readUrl())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  return [state, update]
}

export function shareUrl(state: SandboxState): string {
  const params = new URLSearchParams({ chain: state.network, feed: state.feed })
  return `${window.location.origin}${window.location.pathname}?${params}`
}
