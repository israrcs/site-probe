import type { ReactNode } from 'react'

export default function EmptyState({
  icon,
  title,
  description,
  action,
  className = '',
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={`flex animate-fade-in flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700/80 bg-slate-900/40 px-6 py-14 text-center ${className}`}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 text-3xl shadow-inner ring-1 ring-slate-700">
        {icon ?? '🔍'}
      </div>
      <h3 className="text-base font-semibold text-slate-200">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-slate-500">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}