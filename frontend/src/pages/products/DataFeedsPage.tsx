import { ProductLayout } from '../../components/ProductLayout'
import { SandboxPage } from '../SandboxPage'
import { SEO } from '../../components/SEO'
import { ChartBarIcon } from '../../components/icons/Icon'
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
        icon={ChartBarIcon}
        title="Data Feeds"
        tagline="Price oracle sandbox"
        status="live"
        description={
          <>
            Query 1,400+ live price feeds across 13 mainnets. Browse crypto, forex, equities, commodities, and economic data with historical rounds and aggregation details.
          </>
        }
      >
        <SandboxPage registry={registry} />
      </ProductLayout>
    </>
  )
}
