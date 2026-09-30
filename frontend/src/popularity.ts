/**
 * Popularity scoring for feed ordering.
 *
 * Chainlink publishes no per-feed query counts, so "popularity" is computed as:
 *   1. a curated rank for mainstream base assets (dominant term),
 *   2. chain coverage (how many chains the feed is deployed on),
 *   3. a preference for USD-quoted pairs over exotic quotes.
 * Unranked (long-tail) assets sort strictly below ranked ones, ordered by coverage.
 */

const BASE_ASSET_RANK: Record<string, number> = {
  // Majors
  btc: 100,
  wbtc: 82,
  eth: 99,
  steth: 78,
  wsteth: 76,
  sol: 95,
  xrp: 90,
  bnb: 88,
  doge: 85,
  ada: 83,
  trx: 80,
  ltc: 78,
  dot: 77,
  shib: 74,
  // Chainlink-native audience
  link: 94,
  // L1/L2 majors
  avax: 84,
  matic: 79,
  pol: 79,
  op: 76,
  arb: 78,
  near: 72,
  atom: 73,
  sui: 75,
  apt: 72,
  ton: 74,
  // DeFi blue chips
  uni: 75,
  aave: 76,
  mkr: 70,
  ldo: 68,
  crv: 66,
  comp: 65,
  snx: 64,
  // Stablecoins
  usdt: 89,
  usdc: 89,
  dai: 80,
  // Metals
  xau: 96,
  xag: 91,
  xpt: 70,
  // Energy / commodities
  wti: 92,
  brent: 84,
  oil: 88,
  ngas: 68,
  // Equity indices & ETFs
  spx: 93,
  spy: 90,
  ndx: 87,
  qqq: 84,
  dji: 82,
  // Blue-chip equities
  nvda: 86,
  tsla: 85,
  aapl: 84,
  msft: 83,
  amzn: 82,
  googl: 80,
  goog: 80,
  meta: 79,
  coin: 74,
  mstr: 73,
  hood: 70,
  // Major forex
  eur: 88,
  gbp: 83,
  jpy: 83,
  chf: 78,
  aud: 74,
  cad: 74,
  cny: 72,
  krw: 68,
  inr: 68,
  brl: 66,
  mxn: 65,
  nzd: 64,
  sgd: 64,
  try: 62,
  zar: 62,
}

const USD_QUOTES = new Set(['usd', 'usdc', 'usdt'])

export function isVariantFeed(slug: string): boolean {
  // SVR (Smart Value Recapture) and similar suffixed deployments share a
  // display name with the canonical feed but serve specialized integrations.
  return slug.split('-').length > 2
}

export function popularityScore(slug: string, chainCount: number): number {
  const parts = slug.split('-')
  const base = parts[0]
  const quote = parts[parts.length - 1]

  const rank = BASE_ASSET_RANK[base] ?? 0
  // Exact "<base>-usd" pairs are the canonical feeds; exotic quote pairs of a
  // mainstream asset drop several rank points so canonical feeds of other
  // mainstream assets interleave above them.
  const quotePenalty = rank > 0 && !USD_QUOTES.has(quote) ? 9000 : 0
  // Keep specialized variants (e.g. btc-usd-svr) out of the mainstream top.
  const variantPenalty = rank > 0 && isVariantFeed(slug) ? 25000 : 0

  return rank * 1000 + chainCount - quotePenalty - variantPenalty
}

export function comparePopularity(
  a: { slug: string; chainCount: number; name: string },
  b: { slug: string; chainCount: number; name: string },
): number {
  return (
    popularityScore(b.slug, b.chainCount) - popularityScore(a.slug, a.chainCount) ||
    a.name.localeCompare(b.name)
  )
}
