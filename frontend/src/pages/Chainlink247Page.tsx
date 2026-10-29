import { Link } from 'react-router-dom'
import { PageLayout } from '../components/PageLayout'
import { SEO } from '../components/SEO'
import { CalendarIcon, ChevronRightIcon, ExternalLinkIcon, InfoCircleIcon } from '../components/icons/Icon'

const SOURCES = [
  {
    href: 'https://chain.link/blog/introducing-chainlink-24-7',
    label: 'Introducing Chainlink 24/7',
    note: 'Announcement — now live at Link:NYC, 2026-10-29',
  },
  {
    href: 'https://docs.chain.link/data-streams/market-hours',
    label: 'Data Streams market hours',
    note: 'Session model and marketStatus field',
  },
  {
    href: 'https://docs.chain.link/data-streams/rwa-streams/24-5-us-equities-user-guide',
    label: '24/5 US Equities user guide',
    note: 'marketStatus 0–5; use the report field, never timestamps',
  },
  {
    href: 'https://docs.chain.link/data-feeds/24-7-extended-hours-data-feeds',
    label: '24/7 extended-hours Data Feeds',
    note: 'On-chain feed product docs (stock proxies are not listed yet)',
  },
  {
    href: 'https://docs.chain.link/data-streams/reference/report-schema-v11',
    label: 'Report schema v11',
    note: 'Fuller report shape; today\'s 24/7 streams ship schema v2',
  },
  {
    href: 'https://docs.chain.link/data-feeds/tokenized-equity-feeds',
    label: 'Tokenized equity feeds',
    note: 'Reach out to Chainlink before integrating',
  },
]

export function Chainlink247Page() {
  return (
    <PageLayout>
      <SEO
        title="Chainlink 24/7 explained"
        description="What Chainlink 24/7 is, how Data Feeds differ from Data Streams, what is live today (17 Arbitrum streams and tGLD), what is not on-chain yet, and how access works."
        path="/chainlink-247"
      />

      <article className="mx-auto max-w-3xl">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Reference</p>
        <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Chainlink 24/7 explained</h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          On 29 October 2026 Chainlink launched Chainlink 24/7 at Link:NYC. It extends the existing 24/5 US Equities
          Streams product across weekends and US market holidays. This page is a developer-facing summary of what that
          means for Data Feeds versus Data Streams — and what LinkNodes will and will not show as on-chain.
        </p>

        <section className="mt-8">
          <h2 className="text-base font-bold text-white">What it is</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            24/5 US Equities Streams already publish through pre-market, regular, post, and overnight sessions on the
            NYSE calendar. Chainlink 24/7 keeps publishing when that cash calendar is closed. While traditional markets
            are shut, the price is sourced from perpetual-futures exchanges. Chainlink states that this off-hours price
            is not a live quote from the closed traditional exchange.
          </p>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Aave Horizon is the launch partner and describes the integration as coming soon. Access is not a public
            self-serve subscribe today — teams contact Chainlink.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="text-base font-bold text-white">Feeds vs Streams</h2>
          <div className="mt-3 grid gap-px bg-ink-700 sm:grid-cols-2">
            <div className="bg-ink-900 p-4">
              <h3 className="text-sm font-bold text-white">Data Feeds</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                On-chain aggregator proxies. Anyone can call <code className="text-slate-300">latestRoundData()</code> on
                the proxy address. LinkNodes queries these. 24/5 and NYSE equity feeds pause when the cash market is
                closed — a weekend gap is not a stale oracle.
              </p>
            </div>
            <div className="bg-ink-900 p-4">
              <h3 className="text-sm font-bold text-white">Data Streams</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">
                Off-chain reports delivered through Chainlink&apos;s Streams API and verified on-chain. Identified by a
                <code className="text-slate-300"> feedId</code>, not a proxy. The 17 live 24/7 products are Streams.
                Schema v2 carries a price only — no <code className="text-slate-300">marketStatus</code>.
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-slate-500">
            Streams reports that do include marketStatus use: 0 Unknown, 1 Pre, 2 Regular, 3 Post, 4 Overnight, 5 Closed.
            Chainlink&apos;s docs say to use that field and never timestamps when deciding the session.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="text-base font-bold text-white">What is live now</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-400">
            <li className="border border-ink-700 bg-ink-900 p-3">
              <span className="font-semibold text-white">17 Data Streams on Arbitrum</span> (chain 42161), named like
              {' '}<code className="text-slate-300">TSLA/USD-Streams-247-mainnet-production</code>.
              Stocks: AAPL, GOOGL, MSFT, NVDA, TSLA, MSTR, INTC, MU, HOOD, CRCL, SPCX, SKHY.
              Commodities: XAU, XAG, WTI, BRENT, NGAS. Schema v2.
            </li>
            <li className="border border-ink-700 bg-ink-900 p-3">
              <span className="font-semibold text-white">One on-chain 24/7 blended feed:</span>
              {' '}tGLD/USD on Ethereum at{' '}
              <code className="break-all text-slate-300">0x369C67E8b026CC4Ef98350f332D7Dd52b85b7674</code>.
              That is a tokenized-gold calculated price, not a 24/7 stock Data Feed.
            </li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="text-base font-bold text-white">What is not live yet</h2>
          <div className="mt-3 flex gap-2 border border-ink-700 bg-ink-900 p-3">
            <InfoCircleIcon size={16} className="mt-0.5 shrink-0 text-slate-400" />
            <div className="text-sm leading-relaxed text-slate-400">
              <p>
                There are no on-chain 24/7 stock Data Feeds with proxy addresses in the reference-data directory.
                LinkNodes will not list a 24/7 stock feed as queryable until a proxy exists.
              </p>
              <p className="mt-2">
                Aave Horizon&apos;s 24/7 integration is announced as coming soon. Tokenized equity docs still require
                reaching out to Chainlink before integrating.
              </p>
            </div>
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-base font-bold text-white">Access</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            24/7 Streams access is contact-Chainlink for now. The tokenized equity documentation says to reach out
            before integrating. LinkNodes lists the 17 stream IDs so you can see what shipped; it does not proxy Streams
            reports or invent live weekend stock prints.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="text-base font-bold text-white">How LinkNodes treats market hours</h2>
          <div className="mt-3 flex gap-2 border border-ink-700 bg-ink-900 p-3">
            <CalendarIcon size={16} className="mt-0.5 shrink-0 text-slate-400" />
            <p className="text-sm leading-relaxed text-slate-400">
              Session badges (Open / Pre / Post / Overnight / Closed / Extended) are calculated by LinkNodes from the
              NYSE calendar and US market holidays. They are not an oracle value. For 24/5 and NYSE Data Feeds, a closed
              session shows “Market closed, last update …” instead of stale or unhealthy. Generated snippets use each
              feed&apos;s real heartbeat plus a 900s buffer.
            </p>
          </div>
        </section>

        <section className="mt-8">
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
            to="/rwa"
            className="inline-flex items-center gap-1.5 border border-accent-500 bg-accent-500 px-3 py-2 text-xs font-semibold text-white hover:bg-accent-600"
          >
            Open the RWA hub
            <ChevronRightIcon size={14} />
          </Link>
          <Link
            to="/feeds/ethereum/tgld-usd"
            className="inline-flex items-center gap-1.5 border border-ink-600 bg-ink-800 px-3 py-2 text-xs font-medium text-slate-200 hover:border-ink-500"
          >
            tGLD/USD on Ethereum
          </Link>
        </div>
      </article>
    </PageLayout>
  )
}
