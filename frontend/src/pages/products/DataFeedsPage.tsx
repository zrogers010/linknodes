import { ProductLayout } from '../../components/ProductLayout'
import { SandboxPage } from '../SandboxPage'
import type { Registry } from '../../types'

export function DataFeedsPage({ registry }: { registry: Registry }) {
  return (
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
  )
}
