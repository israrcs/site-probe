import { useMemo, useState } from 'react'
import type { Issue } from '../types'
import { CATEGORY_LABEL, SeverityBadge } from './Badges'
import EmptyState from './EmptyState'

const SEV_ORDER: Record<string, number> = {
  critical: 0, high: 1, medium: 2, low: 3, info: 4,
}

export function shortUrl(u: string): string {
  try {
    const p = new URL(u)
    return p.host + (p.pathname === '/' ? '' : p.pathname)
  } catch {
    return u
  }
}

const selectCls =
  'rounded-lg border border-slate-700 bg-slate-950/60 px-2.5 py-2 text-xs text-slate-300 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20 transition'

export default function IssueTable({
  issues,
  onSelect,
  selectedId,
}: {
  issues: Issue[]
  onSelect: (i: Issue) => void
  selectedId?: string
}) {
  const [category, setCategory] = useState('')
  const [severity, setSeverity] = useState('')
  const [page, setPage] = useState('')
  const [query, setQuery] = useState('')

  const pages = useMemo(
    () => Array.from(new Set(issues.map((i) => i.page_url))).sort(),
    [issues],
  )

  const filtered = useMemo(
    () =>
      issues
        .filter((i) => !category || i.category === category)
        .filter((i) => !severity || i.severity === severity)
        .filter((i) => !page || i.page_url === page)
        .filter(
          (i) =>
            !query ||
            (i.title + ' ' + i.description)
              .toLowerCase()
              .includes(query.toLowerCase()),
        )
        .sort(
          (a, b) =>
            SEV_ORDER[a.severity] - SEV_ORDER[b.severity] ||
            a.page_url.localeCompare(b.page_url),
        ),
    [issues, category, severity, page, query],
  )

  if (issues.length === 0) {
    return (
      <EmptyState
        icon="✨"
        title="No issues found"
        description="This scan ran clean — great job! Every page passed the selected checks."
      />
    )
  }

  return (
    <div className="animate-fade-in space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search issues…"
          className={`${selectCls} w-44`}
        />
        <select value={severity} onChange={(e) => setSeverity(e.target.value)} className={selectCls}>
          <option value="">All severities</option>
          {['critical', 'high', 'medium', 'low', 'info'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className={selectCls}>
          <option value="">All categories</option>
          {Object.entries(CATEGORY_LABEL).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select value={page} onChange={(e) => setPage(e.target.value)} className={`${selectCls} max-w-[220px]`}>
          <option value="">All pages</option>
          {pages.map((p) => (
            <option key={p} value={p}>{shortUrl(p)}</option>
          ))}
        </select>
        <span className="ml-auto text-xs text-slate-500">
          {filtered.length} of {issues.length} issues
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon="🎯"
          title="No issues match these filters"
          description="Try clearing the search text or choosing different severity / category filters."
          action={
            <button onClick={() => { setQuery(''); setSeverity(''); setCategory(''); setPage('') }}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800">
              Clear filters
            </button>
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-3 py-2.5">Severity</th>
                <th className="px-3 py-2.5">Issue</th>
                <th className="px-3 py-2.5">Page</th>
                <th className="px-3 py-2.5">VP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {filtered.map((i) => (
                <tr
                  key={i.id}
                  onClick={() => onSelect(i)}
                  className={`cursor-pointer transition-colors hover:bg-slate-800/40 ${
                    selectedId === i.id ? 'bg-sky-950/40' : ''
                  }`}
                >
                  <td className="px-3 py-2.5 align-top">
                    <SeverityBadge severity={i.severity} />
                  </td>
                  <td className="max-w-md px-3 py-2.5 align-top">
                    <div className="font-medium text-slate-200">{i.title}</div>
                    <div className="mt-0.5 text-[11px] uppercase tracking-wide text-slate-500">
                      {CATEGORY_LABEL[i.category] ?? i.category}
                      {i.selector ? ` · ${i.selector.slice(0, 60)}` : ''}
                    </div>
                  </td>
                  <td className="max-w-[220px] truncate px-3 py-2.5 align-top text-xs text-slate-400">
                    {shortUrl(i.page_url)}
                  </td>
                  <td className="px-3 py-2.5 align-top text-xs text-slate-500">
                    {i.viewport ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
