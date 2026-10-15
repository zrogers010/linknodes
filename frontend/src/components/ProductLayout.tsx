import type { ReactNode, ComponentType, SVGProps } from 'react'

interface ProductLayoutProps {
  icon: ComponentType<SVGProps<SVGSVGElement>>
  title: string
  tagline: string
  status: 'live' | 'preview' | 'coming-soon'
  description: ReactNode
  children: ReactNode
}

const STATUS_CONFIG = {
  live: { label: 'Live Sandbox', className: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' },
  preview: { label: 'Preview', className: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
  'coming-soon': { label: 'Coming Soon', className: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
}

export function ProductLayout({ icon: IconComponent, title, tagline, status, description, children }: ProductLayoutProps) {
  const statusConfig = STATUS_CONFIG[status]
  
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* Product header */}
      <div className="shrink-0 border-b border-ink-700 bg-ink-900 px-4 py-3 sm:px-6">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-ink-600 bg-ink-800 text-accent-400 sm:h-10 sm:w-10">
            <IconComponent width={18} height={18} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-bold text-white sm:text-xl">{title}</h1>
              <span className={`border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${statusConfig.className}`}>
                {statusConfig.label}
              </span>
            </div>
            <p className="mt-0.5 text-xs font-medium text-slate-400 sm:text-sm">{tagline}</p>
            <div className="mt-1.5 text-xs text-slate-500 sm:text-sm">{description}</div>
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
