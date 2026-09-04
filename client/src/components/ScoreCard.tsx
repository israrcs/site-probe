export function scoreColor(score: number): string {
  if (score >= 90) return 'text-emerald-400'
  if (score >= 80) return 'text-lime-400'
  if (score >= 70) return 'text-yellow-400'
  if (score >= 60) return 'text-orange-400'
  return 'text-red-400'
}

export function scoreHex(score: number): string {
  if (score >= 90) return '#34d399'
  if (score >= 80) return '#a3e635'
  if (score >= 70) return '#facc15'
  if (score >= 60) return '#fb923c'
  return '#f87171'
}

export default function ScoreCard({
  label,
  score,
  issues,
}: {
  label: string
  score: number
  issues?: number
}) {
  const clamped = Math.min(100, Math.max(0, score))
  const deg = Math.round(clamped * 3.6)
  const hex = scoreHex(score)
  return (
    <div className="group rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-center transition-colors hover:border-slate-600 hover:bg-slate-900">
      <div
        className="mx-auto h-14 w-14 rounded-full transition-transform duration-300 group-hover:scale-105"
        style={{ background: `conic-gradient(${hex} ${deg}deg, #1e293b ${deg}deg)` }}
        title={`${label}: ${clamped}/100`}
      >
        <div className="m-1 flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
          {clamped}
        </div>
      </div>
      <div className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        {label}
      </div>
      {issues !== undefined && (
        <div className="text-[10px] text-slate-600">{issues} issue(s)</div>
      )}
    </div>
  )
}
