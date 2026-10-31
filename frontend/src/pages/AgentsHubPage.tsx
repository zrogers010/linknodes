import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageLayout } from '../components/PageLayout'
import { SEO } from '../components/SEO'
import { CopyButton } from '../components/CopyButton'
import { apiUrl } from '../config'
import {
  ChevronRightIcon,
  ExternalLinkIcon,
  InfoCircleIcon,
  RobotIcon,
  ShieldCheckIcon,
} from '../components/icons/Icon'

type PriceOverride = {
  chain_selector: string
  price_usdc: string
  network_label?: string
}

type CatalogWorkflow = {
  name: string
  description: string
  kind: string | null
  execute_endpoint: string | null
  price_usdc: string | null
  price_overrides: PriceOverride[]
  price_tier: string | null
}

type AgentsCatalog = {
  generated_at: string | null
  status: string
  count: number
  source_url: string
  workflows: CatalogWorkflow[]
}

const SKILL_INSTALL = 'npx skills add smartcontractkit/chainlink-for-agents'
const CATALOG_CURL = 'curl -sS https://agents.chain.link/v1/catalog'
const DETAIL_CURL = 'curl -sS https://agents.chain.link/v1/catalog/token-transfer'
const LINKNODES_CATALOG_CURL = 'curl -sS https://www.linknodes.io/v1/agents/catalog'

const SOURCES = [
  {
    href: 'https://docs.chain.link/solutions/chainlink-for-agents',
    label: 'Chainlink for Agents docs',
    note: 'Product overview, setup, and 402-then-retry payment flow',
  },
  {
    href: 'https://docs.chain.link/solutions/chainlink-for-agents/guides/set-guardrails',
    label: 'Set guardrails',
    note: 'Link the agent at app.chain.link and bind spend / protocol limits',
  },
  {
    href: 'https://docs.chain.link/solutions/chainlink-for-agents/guides/check-price-and-swap',
    label: 'Check a price and swap',
    note: 'Data Streams read plus a Uniswap swap on Base',
  },
  {
    href: 'https://github.com/smartcontractkit/chainlink-for-agents',
    label: 'Skills repo',
    note: 'npx skills add smartcontractkit/chainlink-for-agents',
  },
  {
    href: 'https://agents.chain.link/.well-known/agent.json',
    label: 'Gateway agent card',
    note: 'agents.chain.link discovery document',
  },
  {
    href: 'https://agents.chain.link/v1/openapi.yaml',
    label: 'Gateway OpenAPI',
    note: 'Full paid API contract',
  },
  {
    href: 'https://app.chain.link/cre/agents',
    label: 'Chainlink platform — Agents',
    note: 'Link an agent and edit guardrails',
  },
]

function Snippet({ code }: { code: string }) {
  return (
    <div className="mt-2 flex items-start gap-2 border border-ink-700 bg-ink-950 px-3 py-2">
      <code className="min-w-0 flex-1 overflow-x-auto font-mono text-[12px] text-slate-300">{code}</code>
      <CopyButton text={code} />
    </div>
  )
}

function formatPrice(item: CatalogWorkflow): string {
  if (item.price_usdc == null || item.price_usdc === '') {
    return 'Not published'
  }
  return `${item.price_usdc} USDC`
}

export function AgentsHubPage() {
  const [catalog, setCatalog] = useState<AgentsCatalog | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)

  useEffect(() => {
    fetch(apiUrl('/v1/agents/catalog'))
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: AgentsCatalog) => {
        setCatalog(data)
        setCatalogError(null)
      })
      .catch((err: unknown) => {
        setCatalogError(err instanceof Error ? err.message : String(err))
      })
  }, [])

  return (
    <PageLayout>
      <SEO
        title="Chainlink for Agents"
        description="Plain-language setup for Chainlink for Agents: skills install, Base USDC, registration, chain wallet, guardrails, and the x402 402-then-retry flow. Live catalog from agents.chain.link."
        path="/agents"
      />

      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-1.5 border border-ink-600 bg-ink-800 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                <RobotIcon size={12} />
                Chainlink for Agents
              </div>
              <span className="border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
                Beta
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Give an agent signed prices and guarded on-chain workflows
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">
              Chainlink for Agents (beta, launched around August 2026) is a hosted gateway plus a skills
              bundle. An AI agent can pull signed Data Streams reports and run catalog workflows — token
              transfer, Uniswap swap, Aave supply/withdraw, CCIP bridge — paid per call in USDC on Base
              via x402. You set guardrails in the Chainlink platform; the agent cannot change them.
            </p>
          </div>
          <a
            href="https://docs.chain.link/solutions/chainlink-for-agents"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 border border-ink-600 bg-ink-800 px-3 py-2 text-xs font-medium text-slate-200 hover:border-ink-500"
          >
            Official docs
            <ExternalLinkIcon size={14} />
          </a>
        </div>

        <div className="mb-8 grid gap-px bg-ink-700 sm:grid-cols-2">
          <div className="bg-ink-900 p-4">
            <h2 className="text-sm font-bold text-white">What it is</h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              Two pieces: the public gateway at{' '}
              <code className="text-slate-300">agents.chain.link</code> and the skills repo your agent
              loads. The gateway builds calldata, sponsors gas on the chain wallet, and checks every
              write against owner-set guardrails. LinkNodes does not execute those paid workflows — it
              explains the product and mirrors the public catalog.
            </p>
          </div>
          <div className="bg-ink-900 p-4">
            <h2 className="text-sm font-bold text-white">What it is not</h2>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              It is not a LinkNodes feature and not a free Data Streams proxy. Paid calls go to
              Chainlink&apos;s gateway. Guardrails apply to the deployed chain wallet (SVA), not to the
              agent&apos;s own key. Keep only fee USDC on the agent address; keep trading funds in the
              chain wallet.
            </p>
          </div>
        </div>

        <section className="mb-8">
          <h2 className="text-base font-bold text-white">Setup</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Official docs say this is enough to get moving. Amounts below are Chainlink&apos;s published
            figures, not measurements from LinkNodes.
          </p>
          <ol className="mt-4 space-y-3">
            <li className="border border-ink-700 bg-ink-900 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">1. Install the skill</p>
              <p className="mt-1 text-sm text-slate-400">
                Point the agent at the skills repo, or install with Vercel&apos;s skills CLI:
              </p>
              <Snippet code={SKILL_INSTALL} />
            </li>
            <li className="border border-ink-700 bg-ink-900 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">2. Base wallet + USDC</p>
              <p className="mt-1 text-sm text-slate-400">
                Have the agent create an EVM wallet. Fund that address with USDC on Base mainnet.
                Chainlink&apos;s quick start says 5 USDC is enough to start. This address is the
                agent&apos;s identity and pays x402 fees. The private key stays on the agent&apos;s machine.
              </p>
            </li>
            <li className="border border-ink-700 bg-ink-900 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">3. Register</p>
              <p className="mt-1 text-sm text-slate-400">
                The agent accepts the Chainlink Terms of Service, pays a small sign-up fee, and
                registers with the gateway. Registration limits it to catalog workflows. Then you
                link it to your organization at{' '}
                <a
                  href="https://app.chain.link/cre/agents"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent-400 hover:text-accent-300"
                >
                  app.chain.link
                </a>
                : paste the agent address, generate a one-time token, let the agent sign it, paste the
                signature back.
              </p>
            </li>
            <li className="border border-ink-700 bg-ink-900 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">4. Deploy a chain wallet</p>
              <p className="mt-1 text-sm text-slate-400">
                Ask the agent to create a chain wallet (Signature Verifying Account) on Base. Official
                docs list this as a 1 USDC one-time deploy — the largest fee in the quick start. The
                agent does not hold a key for this address. Fund the chain wallet with the tokens you
                want it to send, swap, or supply. Reads (Data Streams) do not require an SVA.
              </p>
              <Snippet code="Create a chain wallet for yourself on Base and give me its address." />
            </li>
            <li className="border border-ink-700 bg-ink-900 p-4">
              <div className="flex items-start gap-2">
                <ShieldCheckIcon size={16} className="mt-0.5 shrink-0 text-slate-400" />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">5. Set guardrails</p>
                  <p className="mt-1 text-sm text-slate-400">
                    In the Agents dashboard, turn on Agent Restriction (catalog-only), then cap send
                    limits (per tx and per 24h, in USD), allow or deny Uniswap / Aave / transfers /
                    CCIP bridges, and optionally allowlist recipients. Without guardrails the agent
                    can run any catalog workflow with no spend cap. Only you can change these settings.
                  </p>
                </div>
              </div>
            </li>
          </ol>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-bold text-white">x402: 402, then retry</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Paid gateway routes settle in USDC on Base. There is no API key. Identity and payment are
            separate, per the gateway skill:
          </p>
          <ul className="mt-3 space-y-2 text-sm text-slate-400">
            <li className="border border-ink-700 bg-ink-900 p-3">
              <span className="font-semibold text-white">Identity.</span> Protected routes authenticate
              the agent with EIP-191 headers:{' '}
              <code className="text-slate-300">X-Agent-Address</code>,{' '}
              <code className="text-slate-300">X-Agent-Signature</code>,{' '}
              <code className="text-slate-300">X-Agent-Timestamp</code>.
            </li>
            <li className="border border-ink-700 bg-ink-900 p-3">
              <span className="font-semibold text-white">Payment.</span> Call the route unpaid first.
              The gateway returns <code className="text-slate-300">HTTP 402</code> with payment
              requirements. Sign the x402 USDC challenge and retry the identical request with the
              payment proof. The skill bundle handles this once it is installed.
            </li>
          </ul>
          <div className="mt-3 flex gap-2 border border-ink-700 bg-ink-950 p-3 text-[12px] leading-relaxed text-slate-400">
            <InfoCircleIcon size={14} className="mt-0.5 shrink-0 text-slate-500" />
            <p>
              Discover workflows with an unpaid GET. The list is name + description; each{' '}
              <code className="text-slate-300">/v1/catalog/&#123;name&#125;</code> document adds
              schema, execute path, and a price when the gateway publishes one.
            </p>
          </div>
          <Snippet code={CATALOG_CURL} />
          <Snippet code={DETAIL_CURL} />
        </section>

        <section className="mb-8 border border-ink-700 bg-ink-900 p-5">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-white">Gateway catalog</h2>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">
                Cached from{' '}
                <a
                  href="https://agents.chain.link/v1/catalog"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent-400 hover:text-accent-300"
                >
                  agents.chain.link/v1/catalog
                </a>
                {' '}plus per-item detail. Daily refresh writes a last-good copy; the API retries
                in-process every 30 minutes and keeps that copy if the gateway is down. Price is
                shown only when the unpaid detail document included <code>price_usdc</code>.
              </p>
            </div>
            {catalog?.generated_at && (
              <span className="font-mono text-[10px] text-slate-500">
                cached {catalog.generated_at}
              </span>
            )}
          </div>

          {catalogError && (
            <div className="mb-3 border border-ink-700 bg-ink-950 p-3 text-xs text-slate-400">
              Catalog API unreachable ({catalogError}). The table below needs{' '}
              <code className="text-slate-300">GET /v1/agents/catalog</code>.
            </div>
          )}

          {catalog && catalog.workflows.length > 0 ? (
            <div className="overflow-x-auto border border-ink-700">
              <table className="w-full min-w-[640px] text-left text-xs">
                <thead className="bg-ink-950 text-[10px] uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Name</th>
                    <th className="px-3 py-2 font-semibold">Kind</th>
                    <th className="px-3 py-2 font-semibold">Description</th>
                    <th className="px-3 py-2 font-semibold">Price</th>
                    <th className="px-3 py-2 font-semibold">Execute</th>
                  </tr>
                </thead>
                <tbody>
                  {catalog.workflows.map((item) => (
                    <tr key={item.name} className="border-t border-ink-700 bg-ink-950 hover:bg-ink-900">
                      <td className="px-3 py-2 align-top font-mono text-slate-200">{item.name}</td>
                      <td className="px-3 py-2 align-top text-slate-400">{item.kind || '—'}</td>
                      <td className="px-3 py-2 align-top text-slate-400">{item.description}</td>
                      <td className="px-3 py-2 align-top text-slate-300">
                        <div>{formatPrice(item)}</div>
                        {item.price_overrides?.map((override) => (
                          <div key={override.chain_selector} className="mt-1 text-[10px] text-slate-500">
                            {override.network_label || `selector ${override.chain_selector}`}: {override.price_usdc} USDC
                          </div>
                        ))}
                      </td>
                      <td className="px-3 py-2 align-top font-mono text-[11px] text-slate-400">
                        {item.execute_endpoint || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            !catalogError && (
              <p className="text-xs text-slate-500">Loading catalog…</p>
            )
          )}

          <p className="mt-3 text-[11px] text-slate-500">
            {catalog ? `${catalog.count} items` : ''}
            {catalog?.status ? ` · ${catalog.status}` : ''}
            . Ethereum override labels come from LinkNodes&apos; CCIP registry, not from the gateway.
          </p>
          <Snippet code={LINKNODES_CATALOG_CURL} />
        </section>

        <section className="mb-8">
          <h2 className="text-base font-bold text-white">Machine-readable LinkNodes</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            LinkNodes itself is a free, read-only toolkit. These files describe the site and the
            public <code className="text-slate-300">/v1</code> API — they are not the Chainlink gateway.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {[
              { href: '/llms.txt', label: '/llms.txt', note: 'Short page and API index' },
              { href: '/llms-full.txt', label: '/llms-full.txt', note: 'Longer route-by-route description' },
              { href: '/.well-known/agent.json', label: '/.well-known/agent.json', note: 'LinkNodes agent card' },
              { href: '/v1/openapi.json', label: '/v1/openapi.json', note: 'Public OpenAPI 3 spec for /v1' },
            ].map((item) => (
              <li key={item.href}>
                <a href={item.href} className="inline-flex items-start gap-2 text-accent-400 hover:text-accent-300">
                  <ExternalLinkIcon size={14} className="mt-0.5 shrink-0" />
                  <span>
                    <span className="font-medium">{item.label}</span>
                    <span className="block text-xs text-slate-500">{item.note}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </section>

        <section className="mb-2">
          <h2 className="text-base font-bold text-white">Sources</h2>
          <ul className="mt-3 space-y-2">
            {SOURCES.map((src) => (
              <li key={src.href}>
                <a
                  href={src.href}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-start gap-2 text-sm text-accent-400 hover:text-accent-300"
                >
                  <ExternalLinkIcon size={14} className="mt-0.5 shrink-0" />
                  <span>
                    <span className="font-medium">{src.label}</span>
                    <span className="block text-xs text-slate-500">{src.note}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-10 flex flex-wrap gap-3 border-t border-ink-700 pt-6">
          <Link
            to="/products/data-feeds"
            className="inline-flex items-center gap-1.5 border border-accent-500 bg-accent-500 px-3 py-2 text-xs font-semibold text-white hover:bg-accent-600"
          >
            Data Feeds sandbox
            <ChevronRightIcon size={14} />
          </Link>
          <Link
            to="/rwa"
            className="inline-flex items-center gap-1.5 border border-ink-600 bg-ink-800 px-3 py-2 text-xs font-medium text-slate-200 hover:border-ink-500"
          >
            RWA / 24/7 hub
          </Link>
        </div>
      </div>
    </PageLayout>
  )
}
