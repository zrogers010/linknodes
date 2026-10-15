import { useState } from 'react'
import { CopyIcon, CheckCheckIcon } from './icons/Icon'

export function CopyButton({ text, className = '' }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1400)
  }

  return (
    <button
      onClick={copy}
      title="Copy to clipboard"
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] font-medium transition-colors ${
        copied
          ? 'text-emerald-400'
          : 'text-slate-400 hover:text-slate-200 hover:bg-ink-700'
      } ${className}`}
    >
      {copied ? (
        <>
          <CheckCheckIcon size={14} />
          Copied
        </>
      ) : (
        <CopyIcon size={14} />
      )}
    </button>
  )
}
