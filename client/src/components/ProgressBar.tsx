import type { ProgressEvent } from '../types'

export default function ProgressBar({ event }: { event: ProgressEvent | null }) {
  const pct =
    event && event.pages_total > 0
      ? Math.min(100, Math.round((event.pages_done / event.pages_total) * 100))
      : 4
  return (
    <div className="animate-fade-in rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/80 to-slate-900/40 p-4 backdrop-blur">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="flex items-center gap-2 font-medium text-sky-400">
          <span className="dot-pulse flex items-center gap-0.5 text-sky-400">
            <span />
            <span />
            <span />
          </span>
          {event?.phase ?? 'waiting…'}
        </span>
        <span className="text-slate-400">
          {event?.pages_done ?? 0}/{event?.pages_total ?? 0} pages ·{' '}
          {event?.issue_count ?? 0} issues
        </span>
      </div>
      <div className="flex items-center gap-3">
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-800">
          <div
            className="progress-stripes h-full rounded-full bg-gradient-to-r from-sky-500 to-emerald-500 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="w-10 text-right text-xs font-bold text-slate-300">
          {pct}%
        </span>
      </div>
      {event?.current_url && (
        <div className="mt-2 flex items-center gap-1.5 truncate text-xs text-slate-500">
          <span className="text-slate-600">→</span>
          <span className="truncate font-mono">{event.current_url}</span>
        </div>
      )}
    </div>
  )
}
