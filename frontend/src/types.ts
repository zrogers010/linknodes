export interface FeedMeta {
  name: string
  address: string
  decimals: number | null
  heartbeat: number | null
  deviation_threshold_pct: number | null
  category: string
  feed_type: string
  asset_name: string
  market_hours: string
}

export interface NetworkMeta {
  label: string
  chain_id: number
  explorer: string
  rpc_urls: string[]
  feed_count: number
  feeds: Record<string, FeedMeta>
}

export interface Registry {
  version: string
  source: string
  generated_at: number
  networks: Record<string, NetworkMeta>
}

export interface QueryResult {
  success: boolean
  provider: string
  query_type: string
  meta: Record<string, string | number | null>
  payload: Record<string, string | number>
}

export interface SandboxState {
  network: string
  feed: string
}

export interface CompareRow {
  network: string
  network_label: string
  success: boolean
  price?: number
  unix_timestamp?: number
  staleness_seconds?: number
  contract_address?: string
  explorer_url?: string
  rpc_latency_ms?: number
  cache?: string
  error?: string
}

export interface CompareResponse {
  success: boolean
  feed: string
  summary: {
    chains_queried: number
    chains_ok: number
    total_latency_ms: number
    min?: { network: string; price: number }
    max?: { network: string; price: number }
    spread_bps?: number
  }
  results: CompareRow[]
}
