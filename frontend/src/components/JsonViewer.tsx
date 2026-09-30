import { useMemo } from 'react'
import type { ReactNode } from 'react'

const INDENT = '  '

function renderValue(value: unknown, depth: number, key: number): ReactNode {
  const pad = INDENT.repeat(depth)
  const padInner = INDENT.repeat(depth + 1)

  if (value === null) {
    return <span key={key} className="text-slate-500">null</span>
  }
  if (typeof value === 'boolean') {
    return <span key={key} className="text-violet-400">{String(value)}</span>
  }
  if (typeof value === 'number') {
    return <span key={key} className="text-amber-300">{String(value)}</span>
  }
  if (typeof value === 'string') {
    return <span key={key} className="text-emerald-300">"{value}"</span>
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span key={key}>[]</span>
    return (
      <span key={key}>
        {'[\n'}
        {value.map((item, i) => (
          <span key={i}>
            {padInner}
            {renderValue(item, depth + 1, i)}
            {i < value.length - 1 ? ',' : ''}
            {'\n'}
          </span>
        ))}
        {pad}]
      </span>
    )
  }
  const entries = Object.entries(value as Record<string, unknown>)
  if (entries.length === 0) return <span key={key}>{'{}'}</span>
  return (
    <span key={key}>
      {'{\n'}
      {entries.map(([k, v], i) => (
        <span key={k}>
          {padInner}
          <span className="text-sky-300">"{k}"</span>
          {': '}
          {renderValue(v, depth + 1, i)}
          {i < entries.length - 1 ? ',' : ''}
          {'\n'}
        </span>
      ))}
      {pad}
      {'}'}
    </span>
  )
}

export function JsonViewer({ data }: { data: unknown }) {
  const rendered = useMemo(() => renderValue(data, 0, 0), [data])
  return (
    <pre className="whitespace-pre font-mono text-[12.5px] leading-relaxed text-slate-300">
      {rendered}
    </pre>
  )
}
