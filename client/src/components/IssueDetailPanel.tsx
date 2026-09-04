import { useState } from 'react'
import { artifactUrl } from '../api/client'
import type { Issue } from '../types'
import { CATEGORY_LABEL, SeverityBadge } from './Badges'

function ScreenshotModal({
  src,
  onClose,
}: {
  src: string
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex cursor-zoom-out items-center justify-center bg-black/85 p-6"
      onClick={onClose}
    >
      <img src={src} alt="screenshot" className="max-h-full max-w-full rounded" />
    </div>
  )
}

function ScreenshotBlock({
  runId,
  issue,
  label,
  kind,
}: {
  runId: string
  issue: Issue
  label: string
  kind: string
}) {
  const [zoom, setZoom] = useState(false)
  const rel = issue.screenshot?.[kind]
  if (!rel) return null
  const url = artifactUrl(runId, rel)
  return (
    <div>
      <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <img
        src={url}
        alt={label}
        onClick={() => setZoom(true)}
        className="w-full cursor-zoom-in rounded-md border border-slate-800"
      />
      {zoom && <ScreenshotModal src={url} onClose={() => setZoom(false)} />}
    </div>
  )
}

export default function IssueDetailPanel({
  issue,
  runId,
  onClose,
}: {
  issue: Issue
  runId: string
  onClose: () => void
}) {
  const [copied, setCopied] = useState(false)
  const copySelector = async () => {
    if (!issue.selector) return
    try {
      await navigator.clipboard.writeText(issue.selector)
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <aside className="fixed right-0 top-0 z-40 flex h-full w-full max-w-xl flex-col border-l border-slate-800 bg-slate-950/95 shadow-2xl backdrop-blur">
        <div className="flex items-start justify-between gap-3 border-b border-slate-800 p-4">
          <div>
            <div className="mb-1.5 flex items-center gap-2">
              <SeverityBadge severity={issue.severity} />
              <span className="text-[10px] uppercase tracking-wider text-slate-500">
                {CATEGORY_LABEL[issue.category] ?? issue.category}
              </span>
            </div>
            <h2 className="text-lg font-semibold leading-snug">{issue.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-md border border-slate-800 p-2">
              <div className="text-slate-500">Page</div>
              <a href={issue.page_url} target="_blank" rel="noreferrer" className="break-all text-sky-400 hover:underline">
                {issue.page_url}
              </a>
            </div>
            <div className="rounded-md border border-slate-800 p-2">
              <div className="text-slate-500">Viewport</div>
              <div>{issue.viewport ?? '—'}</div>
            </div>
          </div>

          {issue.description && (
            <p className="text-sm leading-relaxed text-slate-300">{issue.description}</p>
          )}

          {issue.suggestion && (
            <div className="rounded-md border border-emerald-900/60 bg-emerald-950/30 p-3 text-sm text-emerald-300">
              <span className="font-semibold">How to fix: </span>
              {issue.suggestion}
            </div>
          )}

          {issue.selector && (
            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-slate-500">Selector</span>
                <button onClick={copySelector} className="text-[10px] text-sky-400 hover:underline">
                  {copied ? 'copied!' : 'copy'}
                </button>
              </div>
              <code className="block overflow-x-auto rounded-md bg-slate-900 p-2 font-mono text-xs text-sky-300">
                {issue.selector}
              </code>
            </div>
          )}

          {issue.html_snippet && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Element HTML</div>
              <pre className="max-h-40 overflow-auto rounded-md bg-slate-900 p-2 font-mono text-[11px] text-slate-300">
                {issue.html_snippet}
              </pre>
            </div>
          )}

          {issue.metadata && Object.keys(issue.metadata).length > 0 && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Details</div>
              <table className="w-full text-xs">
                <tbody>
                  {Object.entries(issue.metadata).map(([k, v]) => (
                    <tr key={k} className="border-b border-slate-800/60">
                      <td className="py-1 pr-3 align-top text-slate-500">{k}</td>
                      <td className="break-all py-1 text-slate-300">
                        {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <ScreenshotBlock runId={runId} issue={issue} kind="element" label="Element area (where the issue is)" />
          <ScreenshotBlock runId={runId} issue={issue} kind="annotated" label="Full page — issue marked" />
        </div>
      </aside>
    </>
  )
}
