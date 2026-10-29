import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { InfoCircleIcon, XIcon } from './icons/Icon'

const STORAGE_KEY = 'ln-dismiss-chainlink-247'

export function SiteBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    try {
      if (window.localStorage.getItem(STORAGE_KEY) !== '1') {
        setVisible(true)
      }
    } catch {
      setVisible(true)
    }
  }, [])

  if (!visible) return null

  const dismiss = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, '1')
    } catch {
      /* ignore quota / private mode */
    }
    setVisible(false)
  }

  return (
    <div className="border-b border-ink-700 bg-ink-850">
      <div className="flex items-start gap-3 px-4 py-2.5 sm:items-center sm:px-5">
        <InfoCircleIcon size={16} className="mt-0.5 shrink-0 text-accent-400 sm:mt-0" />
        <p className="min-w-0 flex-1 text-[12px] leading-relaxed text-slate-300">
          <span className="font-semibold text-white">Chainlink 24/7</span>
          {' '}is now live as Data Streams on Arbitrum — weekend and holiday prices from perpetual-futures venues.
          {' '}On-chain 24/7 stock Data Feeds are not available yet.{' '}
          <Link to="/rwa" className="font-medium text-accent-400 hover:text-accent-300">
            RWA hub
          </Link>
          <span className="text-slate-600"> · </span>
          <Link to="/chainlink-247" className="font-medium text-accent-400 hover:text-accent-300">
            What changed
          </Link>
        </p>
        <button
          type="button"
          onClick={dismiss}
          className="shrink-0 border border-ink-600 bg-ink-800 p-1 text-slate-400 transition-colors hover:border-ink-500 hover:text-white"
          aria-label="Dismiss Chainlink 24/7 banner"
        >
          <XIcon size={14} />
        </button>
      </div>
    </div>
  )
}
