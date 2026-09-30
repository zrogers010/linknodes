import type { ReactNode } from 'react'

interface ProductLayoutProps {
  icon: string
  title: string
  tagline: string
  status: 'live' | 'preview' | 'coming-soon'
  description: ReactNode
  children: ReactNode
}

const STATUS_CONFIG = {
  live: { label: 'Live Sandbox', className: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  preview: { label: 'Preview', className: 'bg-sky-500/15 text-sky-400 border-sky-500/30' },
  'coming-soon': { label: 'Coming Soon', className: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
}

export function ProductLayout({ icon, title, tagline, status, description, children }: ProductLayoutProps) {
  const statusConfig = STATUS_CONFIG[status]
  
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* Product header */}
      <div className="shrink-0 border-b border-ink-700 bg-ink-900 px-4 py-4 sm:px-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500/20 to-accent-600/20 text-2xl shadow-lg shadow-accent-500/20 sm:h-14 sm:w-14 sm:text-3xl">
            {icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold text-white sm:text-2xl">{title}</h1>
              <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${statusConfig.className}`}>
                {statusConfig.label}
              </span>
            </div>
            <p className="mt-1 text-sm font-semibold text-accent-400 sm:text-base">{tagline}</p>
            <div className="mt-2 text-sm text-slate-400">{description}</div>
          </div>
        </div>
      </div>
      
      {/* Product content */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
