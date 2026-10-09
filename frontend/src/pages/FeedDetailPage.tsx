import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { PageLayout } from '../components/PageLayout'
import { CopyButton } from '../components/CopyButton'
import { SEO } from '../components/SEO'
import { apiUrl } from '../config'

interface FeedData {
  success: boolean
  payload: {
    price: number
    unix_timestamp: number
    staleness_seconds: number
  }
  meta: {
    network: string
    chain_id: number
    feed_name: string
    contract_address: string
    explorer_url: string
    decimals: number
    heartbeat_seconds: number
    deviation_threshold_pct: number
    feed_type: string
    risk_category: string
    resolved_from?: string
    resolved_to?: string
    resolution_note?: string
  }
}

export function FeedDetailPage() {
  const { chain, feed } = useParams<{ chain: string; feed: string }>()
  const [data, setData] = useState<FeedData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!chain || !feed) return

    setLoading(true)
    setError(null)

    fetch(apiUrl(`/v1/query/${chain}/${feed}`))
      .then(async (r) => {
        const json = await r.json()
        if (!r.ok) {
          setError(json.detail || 'Feed not found')
          setData(null)
        } else {
          setData(json)
          setError(null)
        }
      })
      .catch((e) => {
        setError(String(e))
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [chain, feed])

  if (loading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center py-20">
          <div className="text-slate-400">Loading feed data...</div>
        </div>
      </PageLayout>
    )
  }

  if (error || !data) {
    return (
      <PageLayout>
        <SEO
          title={`Feed Not Found - LinkNodes.io`}
          description={`The feed ${feed} on ${chain} was not found.`}
          path={`/feeds/${chain}/${feed}`}
        />
        <div className="mx-auto max-w-3xl py-10">
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-6">
            <h2 className="mb-2 text-lg font-bold text-rose-400">Feed Not Found</h2>
            <p className="mb-4 text-sm text-slate-300">{error || 'This feed does not exist.'}</p>
            <div className="flex gap-2">
              <Link
                to={`/feeds/${chain}`}
                className="rounded-lg bg-ink-700 px-4 py-2 text-sm font-medium text-white hover:bg-ink-600"
              >
                View {chain} feeds
              </Link>
              <Link
                to="/feeds"
                className="rounded-lg bg-ink-700 px-4 py-2 text-sm font-medium text-white hover:bg-ink-600"
              >
                All feeds
              </Link>
            </div>
          </div>
        </div>
      </PageLayout>
    )
  }

  const { meta, payload } = data
  const networkLabel = meta.network.charAt(0).toUpperCase() + meta.network.slice(1)

  // Solidity snippet
  const soliditySnippet = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";

contract PriceConsumer {
    AggregatorV3Interface internal constant FEED =
        AggregatorV3Interface(${meta.contract_address});
    
    function latestPrice() external view returns (int256 price, uint8 decimals) {
        (uint80 roundId, int256 answer,, uint256 updatedAt,) = FEED.latestRoundData();
        require(answer > 0, "Invalid price");
        require(updatedAt > 0, "Round not complete");
        require(roundId > 0, "Invalid round");
        
        uint256 HEARTBEAT = ${meta.heartbeat_seconds};
        require(block.timestamp - updatedAt <= HEARTBEAT + 900, "Stale price");
        
        return (answer, FEED.decimals());
    }
}`

  // JavaScript snippet
  const jsSnippet = `// npm install ethers
import { ethers } from "ethers";

const FEED_ADDRESS = "${meta.contract_address}";
const FEED_ABI = [
  "function latestRoundData() view returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)",
  "function decimals() view returns (uint8)"
];

const provider = new ethers.JsonRpcProvider("YOUR_RPC_URL");
const feed = new ethers.Contract(FEED_ADDRESS, FEED_ABI, provider);

const [roundId, answer, startedAt, updatedAt, answeredInRound] = await feed.latestRoundData();
const decimals = await feed.decimals();

const price = Number(answer) / Math.pow(10, decimals);
console.log("${meta.feed_name}:", price);`

  const seoTitle = `${meta.feed_name} on ${networkLabel} - Live Chainlink Price Feed`
  const seoDescription = `Get ${meta.feed_name} price data from Chainlink on ${networkLabel}. Proxy: ${meta.contract_address}. Heartbeat: ${meta.heartbeat_seconds}s. ${meta.resolution_note ? 'SVR feed with Smart Value Recapture. ' : ''}Free, production-ready code snippets.`

  return (
    <PageLayout>
      <SEO
        title={seoTitle}
        description={seoDescription}
        path={`/feeds/${chain}/${feed}`}
        jsonLd={{
          '@context': 'https://schema.org',
          '@type': 'DataFeed',
          name: meta.feed_name,
          description: `Chainlink ${meta.feed_name} price feed on ${networkLabel}`,
          provider: {
            '@type': 'Organization',
            name: 'Chainlink',
            url: 'https://chain.link'
          },
          url: `https://www.linknodes.io/feeds/${chain}/${feed}`,
          identifier: meta.contract_address
        }}
      />

      <div className="mx-auto max-w-5xl">
        {/* Breadcrumbs */}
        <div className="mb-4 flex items-center gap-2 text-sm">
          <Link to="/feeds" className="text-slate-400 hover:text-accent-300">
            All Feeds
          </Link>
          <span className="text-slate-600">/</span>
          <Link to={`/feeds/${chain}`} className="text-slate-400 hover:text-accent-300">
            {networkLabel}
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-slate-200">{feed}</span>
        </div>

        {/* Feed header */}
        <div className="mb-6 rounded-2xl border border-ink-700 bg-ink-900 p-6">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h1 className="mb-2 text-2xl font-bold text-white">{meta.feed_name}</h1>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">{networkLabel}</span>
                <span className="rounded-full bg-ink-700 px-2 py-0.5 text-xs font-medium text-slate-300">
                  {meta.feed_type}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  meta.risk_category === 'low' ? 'bg-emerald-500/10 text-emerald-400' :
                  meta.risk_category === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                  'bg-slate-700 text-slate-300'
                }`}>
                  {meta.risk_category}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-white">
                ${payload.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
              </div>
              <div className="text-xs text-slate-400">
                Updated {payload.staleness_seconds}s ago
              </div>
            </div>
          </div>

          {/* Resolution note for SVR feeds */}
          {meta.resolution_note && (
            <div className="rounded-lg border border-accent-500/30 bg-accent-500/5 p-3">
              <p className="text-sm text-accent-200">
                <strong>Note:</strong> {meta.resolution_note}
              </p>
              {meta.resolved_from && (
                <p className="mt-1 text-xs text-slate-400">
                  Resolved from <code className="rounded bg-ink-800 px-1">{meta.resolved_from}</code> to{' '}
                  <code className="rounded bg-ink-800 px-1">{meta.resolved_to}</code>
                </p>
              )}
            </div>
          )}
        </div>

        {/* Contract details */}
        <div className="mb-6 rounded-2xl border border-ink-700 bg-ink-900 p-6">
          <h2 className="mb-4 text-base font-bold text-white">Contract Details</h2>
          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-slate-400">Proxy Address</dt>
              <dd className="mt-1 flex items-center gap-2">
                <code className="text-sm text-slate-200">{meta.contract_address}</code>
                <CopyButton text={meta.contract_address} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-400">Decimals</dt>
              <dd className="mt-1 text-sm text-slate-200">{meta.decimals}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-400">Heartbeat</dt>
              <dd className="mt-1 text-sm text-slate-200">{meta.heartbeat_seconds}s ({(meta.heartbeat_seconds / 60).toFixed(0)} minutes)</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-slate-400">Deviation Threshold</dt>
              <dd className="mt-1 text-sm text-slate-200">{meta.deviation_threshold_pct}%</dd>
            </div>
          </dl>
          <div className="mt-4">
            <a
              href={meta.explorer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-accent-400 hover:text-accent-300"
            >
              View on block explorer →
            </a>
          </div>
        </div>

        {/* Code snippets */}
        <div className="space-y-4">
          {/* Solidity */}
          <div className="rounded-2xl border border-ink-700 bg-ink-900">
            <div className="flex items-center justify-between border-b border-ink-700 p-4">
              <h3 className="text-sm font-bold text-white">Solidity</h3>
              <CopyButton text={soliditySnippet} />
            </div>
            <pre className="overflow-x-auto p-4 text-xs leading-relaxed text-slate-300">
              <code>{soliditySnippet}</code>
            </pre>
          </div>

          {/* JavaScript */}
          <div className="rounded-2xl border border-ink-700 bg-ink-900">
            <div className="flex items-center justify-between border-b border-ink-700 p-4">
              <h3 className="text-sm font-bold text-white">JavaScript (ethers.js)</h3>
              <CopyButton text={jsSnippet} />
            </div>
            <pre className="overflow-x-auto p-4 text-xs leading-relaxed text-slate-300">
              <code>{jsSnippet}</code>
            </pre>
          </div>
        </div>

        {/* API example */}
        <div className="mt-6 rounded-xl border border-ink-700 bg-ink-900 p-4">
          <p className="mb-2 text-sm text-slate-400">Query this feed via API:</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-ink-800 px-3 py-2 text-xs text-slate-300">
              {apiUrl(`/v1/query/${chain}/${feed}`)}
            </code>
            <CopyButton text={apiUrl(`/v1/query/${chain}/${feed}`)} />
          </div>
        </div>
      </div>
    </PageLayout>
  )
}
