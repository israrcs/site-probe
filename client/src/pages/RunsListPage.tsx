import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { cancelRun, listRuns } from '../api/client'
import { DemoBadge, StatusBadge } from '../components/Badges'
import EmptyState from '../components/EmptyState'
import { shortUrl } from '../components/IssueTable'
import { scoreColor } from '../components/ScoreCard'
import { SkeletonTable } from '../components/Skeleton'
import type { RunSummary } from '../types'

const SEV_CELL: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-blue-400',
  info: 'text-slate-500',
}

function fmtDuration(s?: number | null): string {
  if (s == null) return '—'
  if (s < 60) return `${Math.round(s)}s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

function fmtAgo(ts?: number | null): string {
  if (!ts) return ''
  const minutes = Math.round((Date.now() / 1000 - ts) / 60)
  if (minutes < 60) return `${Math.max(1, minutes)}m ago`
  if (minutes < 1440) return `${Math.round(minutes / 60)}h ago`
  return `${Math.round(minutes / 1440)}d ago`
}

function RunCards({ runs, onCancel, cancelling }: {
  runs: RunSummary[]
  onCancel: (id: string) => void
  cancelling: Set<string>
}) {
  return (
    <div className="space-y-3 md:hidden">
      {runs.map((r) => (
        <div key={r.id} className="animate-fade-in rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="flex items-center justify-between gap-2">
            <StatusBadge status={r.status} />
            {r.is_demo && <DemoBadge />}
          </div>
          <Link to={`/runs/${r.id}`} className="mt-2 block truncate font-semibold text-sky-400 hover:underline">
            {shortUrl(r.url)}
          </Link>
          <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
            <span>{fmtAgo(r.created_at)} · {r.id}</span>
            <span className={`font-bold ${scoreColor(r.overall_score ?? 100)}`}>
              {r.overall_score ?? '—'}{r.grade ? ` (${r.grade})` : ''}
            </span>
          </div>
          <div className="mt-2 flex select-none gap-3 text-xs">
            {(['critical', 'high', 'medium', 'low', 'info'] as const).map((s) => (
              <span key={s} className={SEV_CELL[s]}>
                {s[0].toUpperCase()}
                <span className="ml-0.5 text-slate-500">{r.issue_counts?.[s] ?? 0}</span>
              </span>
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
            <span>{r.pages_done}/{r.pages_total} pages · {fmtDuration(r.duration_s)}</span>
            {['queued', 'running'].includes(r.status) && (
              <button onClick={() => onCancel(r.id)} disabled={cancelling.has(r.id)}
                className="rounded-md border border-red-800 px-2 py-1 text-red-400 hover:bg-red-950/40 disabled:opacity-40">
                {cancelling.has(r.id) ? '…' : 'Cancel'}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function RunsListPage() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [cancelling, setCancelling] = useState<Set<string>>(new Set())

  const load = useCallback(() => {
    listRuns()
      .then((data) => {
        setRuns(data)
        setLoading(false)
        setError(false)
      })
      .catch(() => {
        setLoading(false)
        setError(true)
      })
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load])

  // Optimistic cancel: flip the row to cancelled immediately, sync afterward.
  const handleCancel = useCallback((id: string) => {
    setRuns((prev) =>
      prev.map((r) => (r.id === id ? { ...r, status: 'cancelled' as const } : r)),
    )
    setCancelling((prev) => new Set(prev).add(id))
    cancelRun(id).catch(() => load()) // revert from server on failure
  }, [load])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Scan history</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Every deep scan you&apos;ve run, with scores and issue counts.
          </p>
        </div>
        {!loading && (
          <Link to="/"
            className="rounded-xl bg-gradient-to-r from-sky-600 to-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-sky-600/20 transition hover:from-sky-500 hover:to-emerald-500">
            + New scan
          </Link>
        )}
      </div>

      {loading && <SkeletonTable rows={6} />}

      {error && (
        <div className="animate-fade-in rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Could not reach the API. Is the server running on port 8000?
        </div>
      )}

      {!loading && !error && runs.length === 0 && (
        <EmptyState
          icon="📡"
          title="No scans yet"
          description="Start your first deep scan to see live progress, annotated screenshots and a full report."
          action={
            <Link to="/"
              className="rounded-xl bg-gradient-to-r from-sky-600 to-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-sky-600/20 transition hover:from-sky-500 hover:to-emerald-500">
              Start your first scan →
            </Link>
          }
        />
      )}

      {!loading && !error && runs.length > 0 && (
        <>
          {/* desktop table */}
          <div className="hidden overflow-hidden rounded-2xl border border-slate-800 md:block">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Target</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Issues</th>
                  <th className="px-4 py-3">Pages</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {runs.map((r) => (
                  <tr key={r.id} className="group transition-colors hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={r.status} />
                        {r.is_demo && <DemoBadge />}
                      </div>
                    </td>
                    <td className="max-w-[260px] px-4 py-3">
                      <Link to={`/runs/${r.id}`} className="block truncate font-medium text-sky-400 hover:underline">
                        {shortUrl(r.url)}
                      </Link>
                      <span className="flex items-center gap-1.5 text-[10px] text-slate-600">
                        {fmtAgo(r.created_at)} · {r.id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-bold ${scoreColor(r.overall_score ?? 100)}`}>
                        {r.overall_score ?? '—'}
                      </span>
                      {r.grade && (
                        <span className="ml-1.5 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold text-slate-300">
                          {r.grade}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex gap-2 text-xs">
                        {(['critical', 'high', 'medium', 'low', 'info'] as const).map((s) => (
                          <span key={s} className={SEV_CELL[s]}>
                            {r.issue_counts?.[s] ?? 0}
                          </span>
                        ))}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {r.pages_done}/{r.pages_total}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {fmtDuration(r.duration_s)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {['queued', 'running'].includes(r.status) && (
                        <button onClick={() => handleCancel(r.id)}
                          disabled={cancelling.has(r.id)}
                          className="rounded-lg border border-red-800/70 px-2.5 py-1 text-xs text-red-400 transition hover:bg-red-950/40 disabled:opacity-40">
                          {cancelling.has(r.id) ? '…' : 'Cancel'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* mobile cards */}
          <RunCards runs={runs} onCancel={handleCancel} cancelling={cancelling} />
        </>
      )}
    </div>
  )
}
