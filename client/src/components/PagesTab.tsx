import { artifactUrl } from '../api/client'
import type { PageResult } from '../types'
import EmptyState from './EmptyState'
import { shortUrl } from './IssueTable'

const statusColor = (s?: number | null) => {
  if (!s) return 'text-slate-500'
  if (s < 300) return 'text-emerald-400'
  if (s < 400) return 'text-sky-400'
  if (s < 500) return 'text-orange-400'
  return 'text-red-400'
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-slate-950/60 px-2 py-1.5 text-center">
      <div className="text-sm font-semibold text-slate-200">{value}</div>
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
    </div>
  )
}

export default function PagesTab({ runId, pages }: { runId: string; pages: PageResult[] }) {
  if (!pages.length) {
    return (
      <EmptyState
        icon="📄"
        title="No pages scanned yet"
        description="Once a scan runs, every crawled page appears here with its screenshots and metrics."
      />
    )
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {pages.map((p) => {
        const m = p.metrics as Record<string, number | null>
        return (
          <div key={p.url} className="animate-fade-in rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
            <div className="flex items-center justify-between gap-2">
              <a href={p.url} target="_blank" rel="noreferrer" className="truncate text-sm font-medium text-sky-400 hover:underline">
                {shortUrl(p.url)}
              </a>
              <span className={`text-sm font-bold ${statusColor(p.status)}`}>
                {p.status ?? '—'}
              </span>
            </div>
            {p.title && (
              <div className="mt-0.5 truncate text-xs text-slate-500">{p.title}</div>
            )}

            <div className="mt-3 flex gap-2 overflow-x-auto">
              {Object.entries(p.screenshots).map(([vp, rel]) => (
                <a key={vp} href={artifactUrl(runId, rel)} target="_blank" rel="noreferrer" className="group relative shrink-0">
                  <img
                    src={artifactUrl(runId, rel)}
                    alt={`${vp} screenshot`}
                    className="h-24 w-auto rounded-lg border border-slate-800 object-cover object-top transition group-hover:border-sky-600"
                  />
                  <span className="absolute bottom-1 right-1 rounded bg-slate-950/80 px-1 text-[9px] uppercase text-slate-400">
                    {vp}
                  </span>
                </a>
              ))}
            </div>

            <div className="mt-3 grid grid-cols-4 gap-1.5">
              <Metric label="Console" value={p.console_errors} />
              <Metric label="Failed req" value={p.failed_requests} />
              <Metric label="TTFB ms" value={m?.ttfb ?? '—'} />
              <Metric label="Weight KB" value={m?.transferKB ?? '—'} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
