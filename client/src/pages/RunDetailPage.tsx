import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  cancelRun,
  getRun,
  reportHtmlUrl,
  reportJsonUrl,
  reportZipUrl,
} from '../api/client'
import { useRunProgress } from '../api/ws'
import { DemoBadge, GradeBadge, SeverityBadge, StatusBadge } from '../components/Badges'
import EmptyState from '../components/EmptyState'
import IssueDetailPanel from '../components/IssueDetailPanel'
import IssueTable from '../components/IssueTable'
import PagesTab from '../components/PagesTab'
import ProgressBar from '../components/ProgressBar'
import ScoreCard from '../components/ScoreCard'
import { SkeletonCards, SkeletonHeader, SkeletonTable } from '../components/Skeleton'
import type { Issue, Run } from '../types'

const ACTIVE = ['queued', 'running']
const CATEGORIES = ['functional', 'console', 'network', 'a11y', 'seo', 'security', 'performance']

export default function RunDetailPage() {
  const { runId = '' } = useParams()
  const [run, setRun] = useState<Run | null>(null)
  const [selected, setSelected] = useState<Issue | null>(null)
  const [tab, setTab] = useState<'issues' | 'pages'>('issues')
  const [notFound, setNotFound] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  const refresh = useCallback(() => {
    getRun(runId).then(setRun).catch(() => setNotFound(true))
  }, [runId])

  useEffect(() => {
    setRun(null)
    setNotFound(false)
    refresh()
  }, [refresh])

  // live progress via WS; `refresh` also fires when the run finishes
  const { event } = useRunProgress(runId, refresh)

  // belt-and-suspenders polling while the run is active
  useEffect(() => {
    if (!run || !ACTIVE.includes(run.status)) return
    const t = setInterval(refresh, 2500)
    return () => clearInterval(t)
  }, [run?.status, refresh])

  // Optimistic cancel: reflect immediately in local state, then sync.
  const onCancel = useCallback(() => {
    if (!run) return
    setCancelling(true)
    setRun({ ...run, status: 'cancelled', phase: 'cancelling…' })
    cancelRun(run.id).catch(refresh)
  }, [run, refresh])

  if (notFound)
    return (
      <EmptyState
        icon="🕳️"
        title="Run not found"
        description="This scan doesn't exist or it was cleared when the API restarted (runs are stored in memory)."
        action={
          <Link to="/" className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500">
            Back to new scan
          </Link>
        }
      />
    )

  if (!run)
    return (
      <div className="space-y-6">
        <SkeletonHeader />
        <SkeletonCards count={8} />
        <SkeletonTable rows={5} />
      </div>
    )

  const isActive = ACTIVE.includes(run.status)
  const isCompleted = run.status === 'completed'
  const counts = run.issues.reduce<Record<string, number>>((acc, i) => {
    acc[i.severity] = (acc[i.severity] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-5">
      <div className="flex animate-fade-in flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <StatusBadge status={run.status} />
          <GradeBadge grade={run.scores?.grade} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <a href={run.options.url} target="_blank" rel="noreferrer"
                className="block max-w-2xl truncate text-lg font-semibold text-sky-400 hover:underline">
                {run.options.url}
              </a>
              {run.is_demo && <DemoBadge />}
            </div>
            <div className="mt-0.5 text-xs text-slate-500">
              {run.pages_done}/{run.pages_total} pages · {run.issues.length} issues
              {run.started_at && run.finished_at &&
                ` · ${Math.round(run.finished_at - run.started_at)}s`}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isCompleted && (
            <>
              <a href={reportHtmlUrl(run.id)} target="_blank" rel="noreferrer"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800">
                HTML report
              </a>
              <a href={reportJsonUrl(run.id)} target="_blank" rel="noreferrer"
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800">
                JSON
              </a>
              <a href={reportZipUrl(run.id)}
                className="rounded-lg bg-gradient-to-r from-sky-600 to-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-lg shadow-sky-600/20 transition hover:from-sky-500 hover:to-emerald-500">
                Download ZIP
              </a>
            </>
          )}
          {isActive && (
            <button onClick={onCancel} disabled={cancelling}
              className="rounded-lg border border-red-800 px-3 py-1.5 text-xs text-red-400 transition hover:bg-red-950/40 disabled:opacity-40">
              {cancelling ? 'Cancelling…' : 'Cancel run'}
            </button>
          )}
        </div>
      </div>

      {run.error && (
        <div className="animate-fade-in rounded-xl border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          {run.error}
        </div>
      )}

      {isActive && <ProgressBar event={event} />}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        <ScoreCard label="Overall" score={run.scores?.overall ?? 100} />
        {CATEGORIES.map((c) => (
          <ScoreCard key={c} label={c} score={run.scores?.categories?.[c] ?? 100}
            issues={run.issues.filter((i) => i.category === c).length} />
        ))}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        {(['critical', 'high', 'medium', 'low', 'info'] as const).map((s) => (
          <span key={s} className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1">
            <SeverityBadge severity={s} /> {counts[s] ?? 0}
          </span>
        ))}
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-slate-800">
        {(['issues', 'pages'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`whitespace-nowrap px-4 py-2 text-sm capitalize transition-colors ${tab === t ? 'border-b-2 border-sky-500 text-white' : 'text-slate-400 hover:text-white'}`}>
            {t}
            {t === 'issues' ? ` (${run.issues.length})` : ` (${run.pages.length})`}
          </button>
        ))}
      </div>

      {tab === 'issues' ? (
        <IssueTable
          issues={run.issues}
          onSelect={setSelected}
          selectedId={selected?.id}
        />
      ) : (
        <PagesTab runId={run.id} pages={run.pages} />
      )}

      {selected && (
        <IssueDetailPanel issue={selected} runId={run.id} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
