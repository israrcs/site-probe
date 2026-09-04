import type { Category, RunStatus, Severity } from '../types'

export const CATEGORY_LABEL: Record<Category, string> = {
  functional: 'Functional',
  console: 'Console',
  network: 'Network',
  a11y: 'Accessibility',
  seo: 'SEO',
  security: 'Security',
  performance: 'Performance',
}

const SEV_STYLE: Record<Severity, string> = {
  critical: 'bg-red-600/20 text-red-400 border-red-600/40',
  high: 'bg-orange-600/20 text-orange-400 border-orange-600/40',
  medium: 'bg-yellow-600/20 text-yellow-500 border-yellow-600/40',
  low: 'bg-blue-600/20 text-blue-400 border-blue-600/40',
  info: 'bg-slate-600/20 text-slate-400 border-slate-600/40',
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${SEV_STYLE[severity]}`}
    >
      {severity}
    </span>
  )
}

const STATUS_STYLE: Record<RunStatus, string> = {
  queued: 'bg-slate-700/40 text-slate-300 border-slate-600',
  running: 'bg-sky-600/20 text-sky-400 border-sky-600/40 animate-pulse',
  completed: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/40',
  failed: 'bg-red-600/20 text-red-400 border-red-600/40',
  cancelled: 'bg-yellow-600/20 text-yellow-500 border-yellow-600/40',
}

export function DemoBadge() {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-amber-400/40 bg-amber-400/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
      ✦ demo
    </span>
  )
}

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded border px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[status]}`}
    >
      {status}
    </span>
  )
}

export function GradeBadge({ grade }: { grade?: string | null }) {
  if (!grade) return null
  const style =
    grade === 'A'
      ? 'from-emerald-500 to-lime-500'
      : grade === 'B'
        ? 'from-lime-500 to-yellow-500'
        : grade === 'C'
          ? 'from-yellow-500 to-orange-500'
          : grade === 'D'
            ? 'from-orange-500 to-red-500'
            : 'from-red-600 to-rose-700'
  return (
    <span
      className={`inline-flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br ${style} text-lg font-black text-slate-950`}
    >
      {grade}
    </span>
  )
}
