import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { PageLayout } from '../components/PageLayout'
import { SEO } from '../components/SEO'
import { apiUrl } from '../config'

interface Registry {
  version: string
  networks: Record<string, {
    label: string
    chain_id: number
    feed_count: number
    feeds: Record<string, {
      name: string
      address: string
      decimals: number
      category: string
      feed_type: string
    }>
  }>
}

export function FeedIndexPage() {
  const { chain } = useParams<{ chain?: string }>()
  const [registry, setRegistry] = useState<Registry | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(apiUrl('/v1/registry'))
      .then((r) => r.json())
      .then(setRegistry)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const networkData = chain && registry ? registry.networks[chain] : null

  // All feeds for selected chain or all chains
  const feeds = useMemo(() => {
    if (!registry) return []
    
    if (chain && networkData) {
      return Object.entries(networkData.feeds).map(([slug, feed]) => ({
        slug,
        chain,
        chainLabel: networkData.label,
        ...feed
      }))
    }

    // All feeds across all chains
    const allFeeds: any[] = []
    Object.entries(registry.networks).forEach(([chainKey, network]) => {
      Object.entries(network.feeds).forEach(([slug, feed]) => {
        allFeeds.push({
          slug,
          chain: chainKey,
          chainLabel: network.label,
          ...feed
        })
      })
    })
    return allFeeds
  }, [registry, chain, networkData])

  // Filtered feeds based on search
  const filteredFeeds = useMemo(() => {
    if (!searchQuery) return feeds
    const query = searchQuery.toLowerCase()
    return feeds.filter(f =>
      f.slug.toLowerCase().includes(query) ||
      f.name.toLowerCase().includes(query) ||
      f.chainLabel.toLowerCase().includes(query)
    )
  }, [feeds, searchQuery])

  // Group by category
  const groupedFeeds = useMemo(() => {
    const groups: Record<string, typeof feeds> = {}
    filteredFeeds.forEach(feed => {
      const category = feed.feed_type || 'Other'
      if (!groups[category]) groups[category] = []
      groups[category].push(feed)
    })
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [filteredFeeds])

  if (loading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center py-20">
          <div className="text-slate-400">Loading feeds...</div>
        </div>
      </PageLayout>
    )
  }

  if (chain && !networkData) {
    return (
      <PageLayout>
        <SEO
          title="Network Not Found - LinkNodes.io"
          description={`The network ${chain} was not found.`}
          path={`/feeds/${chain}`}
        />
        <div className="mx-auto max-w-3xl py-10">
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-6">
            <h2 className="mb-2 text-lg font-bold text-rose-400">Network Not Found</h2>
            <p className="mb-4 text-sm text-slate-300">The network "{chain}" does not exist.</p>
            <Link
              to="/feeds"
              className="inline-block rounded-lg bg-ink-700 px-4 py-2 text-sm font-medium text-white hover:bg-ink-600"
            >
              View all feeds
            </Link>
          </div>
        </div>
      </PageLayout>
    )
  }

  const pageTitle = chain
    ? `${networkData?.label} Data Feeds - ${networkData?.feed_count} Chainlink Feeds`
    : `1,400+ Chainlink Data Feeds - All Networks`
  
  const pageDescription = chain
    ? `Browse ${networkData?.feed_count} live Chainlink price feeds on ${networkData?.label}. Get proxy addresses, heartbeats, and production-ready code snippets for ${networkData?.label} data feeds.`
    : `Browse 1,400+ live Chainlink Data Feeds across 13 mainnet networks. Get proxy addresses, latest prices, heartbeats, and production-ready code snippets for any feed.`

  return (
    <PageLayout>
      <SEO
        title={pageTitle}
        description={pageDescription}
        path={chain ? `/feeds/${chain}` : '/feeds'}
      />

      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <div className="mb-4">
            {chain && (
              <Link to="/feeds" className="mb-2 inline-flex items-center text-sm text-slate-400 hover:text-accent-300">
                ← All Networks
              </Link>
            )}
            <h1 className="text-2xl font-bold text-white">
              {chain ? `${networkData?.label} Data Feeds` : 'Chainlink Data Feeds'}
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              {chain
                ? `${networkData?.feed_count} feeds on ${networkData?.label}`
                : `${feeds.length} feeds across ${Object.keys(registry?.networks || {}).length} networks`}
            </p>
          </div>

          {/* Search */}
          <input
            type="text"
            placeholder="Search feeds..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
          />
        </div>

        {/* Network grid if viewing all feeds */}
        {!chain && registry && (
          <div className="mb-8">
            <h2 className="mb-4 text-base font-bold text-white">Browse by Network</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(registry.networks).map(([key, network]) => (
                <Link
                  key={key}
                  to={`/feeds/${key}`}
                  className="rounded-xl border border-ink-700 bg-ink-900 p-4 transition-colors hover:border-accent-500/50 hover:bg-ink-800"
                >
                  <div className="mb-1 font-medium text-white">{network.label}</div>
                  <div className="text-sm text-slate-400">{network.feed_count} feeds</div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Feeds list */}
        {groupedFeeds.length === 0 ? (
          <div className="rounded-xl border border-ink-700 bg-ink-900 p-6 text-center text-slate-400">
            No feeds found matching "{searchQuery}"
          </div>
        ) : (
          <div className="space-y-6">
            {groupedFeeds.map(([category, categoryFeeds]) => (
              <div key={category}>
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-400">
                  {category}
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryFeeds.map((feed) => (
                    <Link
                      key={`${feed.chain}-${feed.slug}`}
                      to={`/feeds/${feed.chain}/${feed.slug}`}
                      className="rounded-xl border border-ink-700 bg-ink-900 p-4 transition-colors hover:border-accent-500/50 hover:bg-ink-800"
                    >
                      <div className="mb-2 flex items-start justify-between">
                        <div className="font-medium text-white">{feed.name}</div>
                        <span className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                          feed.category === 'low' ? 'bg-emerald-500/10 text-emerald-400' :
                          feed.category === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {feed.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        {!chain && <span>{feed.chainLabel}</span>}
                        <span className="text-slate-600">•</span>
                        <code className="text-slate-500">{feed.slug}</code>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageLayout>
  )
}
