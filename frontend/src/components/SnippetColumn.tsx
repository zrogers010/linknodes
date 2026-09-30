import { useState } from 'react'
import type { Lang } from '../snippets'
import { buildSnippet } from '../snippets'
import type { Registry, SandboxState } from '../types'
import { CopyButton } from './CopyButton'

const LANG_TABS: { id: Lang; label: string }[] = [
  { id: 'solidity', label: 'Solidity' },
  { id: 'javascript', label: 'JS · Ethers' },
  { id: 'python', label: 'Python' },
  { id: 'curl', label: 'cURL' },
]

export function SnippetColumn({ registry, state }: { registry: Registry; state: SandboxState }) {
  const [lang, setLang] = useState<Lang>('solidity')
  const code = buildSnippet(registry, state, lang)

  return (
    <aside className="flex h-full flex-col border-l border-ink-700 bg-ink-900">
      <div className="border-b border-ink-700 p-4 pb-3">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          Integration Snippets
        </h2>
        <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
          Production-ready code for your exact selection. Updates live as you change the route.
        </p>
      </div>

      <div className="flex gap-1 border-b border-ink-700 px-3 pt-2">
        {LANG_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setLang(tab.id)}
            className={`rounded-t-md px-3 py-1.5 text-[12px] font-medium transition-colors ${
              lang === tab.id
                ? 'border border-b-0 border-ink-600 bg-ink-950 text-accent-300'
                : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-ink-950 p-4">
        <div className="absolute right-2 top-2 z-10 rounded-md bg-ink-850/90 backdrop-blur">
          <CopyButton text={code} className="px-2 py-1" />
        </div>
        <pre className="whitespace-pre font-mono text-[11.5px] leading-relaxed text-slate-300">
          {code}
        </pre>
      </div>
    </aside>
  )
}
