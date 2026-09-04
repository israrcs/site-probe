import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startRun } from '../api/client'
import { ALL_CATEGORIES, ALL_VIEWPORTS } from '../types'
import type { Category, RunOptions, Viewport } from '../types'

const CATEGORY_LABELS: Record<Category, string> = {
  functional: 'Functional (links, images, pages)',
  console: 'Console errors',
  network: 'Network failures (4xx/5xx)',
  a11y: 'Accessibility (axe-core WCAG)',
  seo: 'SEO (title, meta, headings…)',
  security: 'Security (headers, HTTPS, cookies)',
  performance: 'Performance (TTFB, LCP, CLS…)',
}

const QUICK_URLS = ['example.com', 'shop.example.com', 'blog.example.org']

const inputCls =
  'w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3.5 py-2.5 text-sm placeholder-slate-600 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20 transition'
const chip =
  'cursor-pointer rounded-lg border px-2.5 py-1.5 text-xs transition-colors'

export default function NewRunPage() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [maxPages, setMaxPages] = useState(10)
  const [viewports, setViewports] = useState<Viewport[]>(['desktop'])
  const [engines, setEngines] = useState<Category[]>([...ALL_CATEGORIES])
  const [followRobots, setFollowRobots] = useState(false)
  const [delayMs, setDelayMs] = useState(0)
  const [timeoutMs, setTimeoutMs] = useState(60000)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggle = <T,>(list: T[], v: T, set: (l: T[]) => void) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim() || starting) return
    setStarting(true)
    setError(null)
    const opts: RunOptions = {
      url: url.trim(),
      max_pages: maxPages,
      viewports: viewports.length ? viewports : ['desktop'],
      engines: engines.length ? engines : [...ALL_CATEGORIES],
      follow_robots: followRobots,
      delay_ms: delayMs,
      timeout_ms: timeoutMs,
      user_agent: null,
    }
    try {
      const res = await startRun(opts)
      navigate(`/runs/${res.id}`)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data
          ?.detail ?? String(err)
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
      setStarting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="animate-fade-in text-center sm:text-left">
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Deep-scan{' '}
          <span className="bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent">
            any website
          </span>
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-slate-400 sm:mx-0">
          SiteProbe crawls a site in a real browser, then checks links, console
          errors, accessibility, SEO, security headers and performance — every
          issue is pinned to an annotated screenshot.
        </p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span>Try:</span>
        {QUICK_URLS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setUrl(q)}
            className="rounded-full border border-slate-700 px-3 py-1 font-mono text-sky-400 transition hover:border-sky-500 hover:bg-sky-500/10"
          >
            {q}
          </button>
        ))}
      </div>

      <form
        onSubmit={submit}
        className="mt-5 space-y-5 rounded-2xl border border-slate-800 bg-slate-900/40 p-5 shadow-xl shadow-slate-950/40 backdrop-blur sm:p-6"
      >
        <div>
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
            Target URL
          </label>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="example.com or https://example.com"
            className={`${inputCls} text-base`}
            autoFocus
          />
          {!url.trim() && (
            <p className="mt-1.5 text-xs text-slate-600">
              Tip: pick one of the demo sites above, or paste any public URL.
            </p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs uppercase tracking-wider text-slate-500">
              Max pages: {maxPages}
            </label>
            <input type="range" min={1} max={50} value={maxPages}
              onChange={(e) => setMaxPages(+e.target.value)}
              className="w-full accent-sky-500" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs uppercase tracking-wider text-slate-500">
              Page timeout: {timeoutMs / 1000}s
            </label>
            <input type="range" min={5} max={120} step={5} value={timeoutMs / 1000}
              onChange={(e) => setTimeoutMs(+e.target.value * 1000)}
              className="w-full accent-sky-500" />
          </div>
        </div>

        <div className="grid gap-3">
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
            Viewports (screenshots + responsive checks)
          </label>
          <div className="grid grid-cols-3 gap-2">
            {ALL_VIEWPORTS.map((v) => (
              <button type="button" key={v}
                onClick={() => toggle(viewports, v, setViewports)}
                className={`${chip} py-2 text-center ${viewports.includes(v) ? 'border-sky-500 bg-sky-500/10 font-semibold text-sky-300' : 'border-slate-700 text-slate-400 hover:border-slate-500'}`}>
                {v}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
            Test engines
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            {ALL_CATEGORIES.map((c) => (
              <label key={c}
                className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-slate-800 px-3 py-2.5 text-xs transition-colors hover:border-slate-600 hover:bg-slate-800/30">
                <input type="checkbox" checked={engines.includes(c)}
                  onChange={() => toggle(engines, c, setEngines)}
                  className="h-3.5 w-3.5 accent-sky-500" />
                <span className="text-slate-300">{CATEGORY_LABELS[c]}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input type="checkbox" checked={followRobots}
              onChange={() => setFollowRobots(!followRobots)}
              className="h-3.5 w-3.5 accent-sky-500" />
            Respect robots.txt (off = scan without restrictions)
          </label>
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">
              Delay between pages: {delayMs} ms
            </label>
            <input type="range" min={0} max={5000} step={250} value={delayMs}
              onChange={(e) => setDelayMs(+e.target.value)}
              className="w-full accent-sky-500" />
          </div>
        </div>

        {error && (
          <div className="animate-fade-in rounded-xl border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <button type="submit" disabled={starting || !url.trim()}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-emerald-600 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-600/20 transition-all hover:from-sky-500 hover:to-emerald-500 hover:shadow-sky-500/30 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:shadow-none">
          {starting ? (
            <>
              <span className="dot-pulse flex items-center gap-1"><span /><span /><span /></span>
              Starting scan…
            </>
          ) : (
            <>Start deep scan →</>
          )}
        </button>
        {starting && (
          <p className="text-center text-xs text-slate-500">
            Launching a Chromium browser and crawling the site…
          </p>
        )}
      </form>
    </div>
  )
}
