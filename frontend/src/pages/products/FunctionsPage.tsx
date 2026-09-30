import { useState } from 'react'
import { ProductLayout } from '../../components/ProductLayout'

const EXAMPLE_SCRIPTS = [
  {
    name: 'Fetch API Data',
    code: `// Fetch cryptocurrency price from CoinGecko API
const url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd'
const response = await Functions.makeHttpRequest({ url })
const price = response.data.bitcoin.usd
return Functions.encodeUint256(Math.round(price * 100))`,
  },
  {
    name: 'Calculate Average',
    code: `// Fetch prices from multiple sources and return average
const sources = [
  'https://api.example.com/price1',
  'https://api.example.com/price2',
  'https://api.example.com/price3'
]
const responses = await Promise.all(
  sources.map(url => Functions.makeHttpRequest({ url }))
)
const prices = responses.map(r => r.data.price)
const average = prices.reduce((a, b) => a + b) / prices.length
return Functions.encodeUint256(Math.round(average * 100))`,
  },
  {
    name: 'Weather Oracle',
    code: `// Get weather data from API
const apiKey = secrets.WEATHER_API_KEY
const url = \`https://api.openweathermap.org/data/2.5/weather?q=\${args[0]}&appid=\${apiKey}\`
const response = await Functions.makeHttpRequest({ url })
const temp = response.data.main.temp
return Functions.encodeInt256(Math.round((temp - 273.15) * 100))`,
  },
]

export function FunctionsPage() {
  const [selectedScript, setSelectedScript] = useState(0)
  const [customCode, setCustomCode] = useState(EXAMPLE_SCRIPTS[0].code)
  
  return (
    <ProductLayout
      icon="⚡"
      title="Chainlink Functions"
      tagline="Serverless Web2 Compute for Smart Contracts"
      status="preview"
      description={
        <>
          Run custom JavaScript on Chainlink's decentralized oracle network. Fetch any API, run computations off-chain, and bring the results on-chain with cryptographic proof. The ultimate bridge between Web2 and Web3.
        </>
      }
    >
      <div className="p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          {/* Capabilities grid */}
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">🌐</div>
              <h3 className="mb-1 text-sm font-bold text-white">Any API</h3>
              <p className="text-xs text-slate-400">
                Call any HTTP endpoint — REST APIs, GraphQL, webhooks, authenticated services
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">🔐</div>
              <h3 className="mb-1 text-sm font-bold text-white">Secrets Management</h3>
              <p className="text-xs text-slate-400">
                Store API keys and credentials encrypted. Access them securely in your scripts
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">⚙️</div>
              <h3 className="mb-1 text-sm font-bold text-white">Custom Logic</h3>
              <p className="text-xs text-slate-400">
                Run JavaScript computations, data transformations, and aggregations
              </p>
            </div>
            <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
              <div className="mb-2 text-2xl">🔗</div>
              <h3 className="mb-1 text-sm font-bold text-white">Decentralized</h3>
              <p className="text-xs text-slate-400">
                Consensus across multiple nodes ensures tamper-proof results
              </p>
            </div>
          </div>

          {/* Code playground */}
          <div className="rounded-2xl border border-ink-700 bg-ink-900">
            <div className="border-b border-ink-700 p-5">
              <h2 className="text-lg font-bold text-white">Function Builder (Preview)</h2>
              <p className="mt-1 text-sm text-slate-400">
                Explore example Functions scripts. Full sandbox with testnet execution coming soon.
              </p>
            </div>
            
            <div className="grid lg:grid-cols-[200px_1fr]">
              {/* Script selector */}
              <div className="border-b border-ink-700 bg-ink-950 p-4 lg:border-b-0 lg:border-r">
                <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Examples
                </h3>
                <div className="space-y-1">
                  {EXAMPLE_SCRIPTS.map((script, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setSelectedScript(idx)
                        setCustomCode(script.code)
                      }}
                      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        selectedScript === idx
                          ? 'bg-accent-500/15 font-semibold text-accent-300'
                          : 'text-slate-400 hover:bg-ink-800 hover:text-slate-200'
                      }`}
                    >
                      {script.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Code editor */}
              <div className="p-5">
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    JavaScript Source
                  </label>
                  <div className="flex gap-2">
                    <button className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-1.5 text-xs font-semibold text-slate-400 transition-colors hover:border-accent-500 hover:text-accent-300">
                      Format
                    </button>
                    <button className="rounded-lg border border-accent-500/50 bg-accent-500/10 px-3 py-1.5 text-xs font-semibold text-accent-300 transition-colors hover:bg-accent-500/20">
                      Test (Coming Soon)
                    </button>
                  </div>
                </div>
                <textarea
                  value={customCode}
                  onChange={(e) => setCustomCode(e.target.value)}
                  className="h-64 w-full rounded-lg border border-ink-600 bg-ink-950 p-4 font-mono text-sm text-slate-200 outline-none focus:border-accent-500"
                  spellCheck={false}
                />
                <div className="mt-3 rounded-lg border border-ink-700 bg-ink-950 p-3">
                  <div className="flex items-start gap-2">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <p className="text-xs text-slate-400">
                      Functions scripts run in a sandboxed JavaScript environment with access to <code className="rounded bg-ink-800 px-1 py-0.5 text-accent-300">Functions.makeHttpRequest()</code>, <code className="rounded bg-ink-800 px-1 py-0.5 text-accent-300">secrets</code>, and <code className="rounded bg-ink-800 px-1 py-0.5 text-accent-300">args</code>.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Execution preview */}
            <div className="border-t border-ink-700 bg-ink-950 p-5">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Execution Flow
              </h3>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 rounded-lg bg-ink-900 px-4 py-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">1</div>
                  <span className="text-sm text-slate-300">Contract calls Function</span>
                </div>
                <svg className="h-4 w-4 text-slate-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                <div className="flex items-center gap-2 rounded-lg bg-ink-900 px-4 py-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">2</div>
                  <span className="text-sm text-slate-300">DON executes script</span>
                </div>
                <svg className="h-4 w-4 text-slate-600" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                <div className="flex items-center gap-2 rounded-lg bg-ink-900 px-4 py-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-500/20 text-xs font-bold text-accent-300">3</div>
                  <span className="text-sm text-slate-300">Result returned on-chain</span>
                </div>
              </div>
            </div>
          </div>

          {/* Use cases */}
          <div className="mt-8">
            <h2 className="mb-4 text-lg font-bold text-white">What You Can Build</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>📊</span>
                  <span>Custom Price Feeds</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Aggregate data from any API to create custom price feeds for long-tail assets or specialized markets.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🔔</span>
                  <span>Event-driven Actions</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Monitor external systems and trigger on-chain actions when specific conditions are met.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎯</span>
                  <span>Sports & Gaming</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Bring real-world event outcomes on-chain for prediction markets, fantasy sports, and gaming.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🌡️</span>
                  <span>IoT & Real-world Data</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Connect IoT sensors, weather data, shipping info, or any real-world data stream to your contract.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🔍</span>
                  <span>Data Aggregation</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Combine multiple data sources, compute averages, detect outliers, and deliver high-quality feeds.
                </p>
              </div>
              <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-white">
                  <span>🎨</span>
                  <span>Dynamic NFTs</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Update NFT metadata based on real-world events, social stats, or any external data source.
                </p>
              </div>
            </div>
          </div>

          {/* Resources */}
          <div className="mt-8 rounded-xl border border-accent-500/30 bg-accent-500/5 p-5">
            <h3 className="mb-3 text-sm font-bold text-white">Coming Soon: Interactive Testnet Executor</h3>
            <p className="mb-4 text-sm text-slate-400">
              We're building a full Functions playground with live testnet execution, real-time logs, and gas estimation. In the meantime, explore the official resources:
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://docs.chain.link/chainlink-functions"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                Functions Documentation
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
              <a
                href="https://functions.chain.link"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg border border-ink-600 bg-ink-800 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:border-accent-500 hover:text-accent-300"
              >
                Functions Playground
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </ProductLayout>
  )
}
