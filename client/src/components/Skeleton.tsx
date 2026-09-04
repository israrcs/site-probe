export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-md ${className}`} />
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={`h-3 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  )
}

export function SkeletonCards({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-center">
          <Skeleton className="mx-auto h-12 w-12 rounded-full" />
          <Skeleton className="mx-auto mt-2 h-2 w-14" />
        </div>
      ))}
    </div>
  )
}

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-3 px-3 py-3">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className={`h-4 ${i === 0 ? 'w-20' : i === 1 ? 'flex-1' : 'w-16'}`} />
      ))}
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900/30">
      <div className="bg-slate-900">
        <SkeletonRow cols={5} />
      </div>
      <div className="divide-y divide-slate-800/70">
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonRow key={i} cols={5} />
        ))}
      </div>
    </div>
  )
}

export function SkeletonHeader() {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-9 rounded-full" />
        <div className="space-y-1.5">
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-3 w-40" />
        </div>
      </div>
      <Skeleton className="h-8 w-44" />
    </div>
  )
}