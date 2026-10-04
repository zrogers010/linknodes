import { ProductLayout } from '../../components/ProductLayout'
import { SandboxPage } from '../SandboxPage'
import { SEO } from '../../components/SEO'
import type { Registry } from '../../types'

export function DataFeedsPage({ registry }: { registry: Registry }) {
  return (
    <>
      <SEO 
        title="Data Feeds — Live Chainlink Price Oracle Sandbox"
        description="Query 1,400+ live Chainlink Data Feeds across 13 mainnets. Test price feeds for crypto, forex, equities, commodities, and macro data with sub-minute updates."
        path="/products/data-feeds"
      />
      <ProductLayout
        icon="📊"
        title="Data Feeds"
        tagline="Real-time Price Oracles"
        status="live"
        description={
          <>
            Query 1,400+ live price feeds across 13 chains. Get crypto, forex, equities, commodities, and macro data on-chain with sub-minute updates and cryptographic guarantees.
          </>
        }
      >
        <SandboxPage registry={registry} />
      </ProductLayout>
    </>
  )
}
