import axios from 'axios'
import type { Run, RunOptions, RunSummary } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

// Detect if we're on a static-only deployment (Vercel without a backend).
// In that case, the UI falls back to built-in demo data for a live preview.
export const IS_STATIC_DEPLOYMENT = typeof window !== 'undefined' &&
  window.location.hostname.includes('vercel.app')

export const api = axios.create({
  baseURL: IS_STATIC_DEPLOYMENT ? '/__offline__' : API_BASE,
  timeout: IS_STATIC_DEPLOYMENT ? 1000 : 15000,
})

export const artifactUrl = (runId: string, rel: string) =>
  IS_STATIC_DEPLOYMENT ? '' : `${API_BASE}/artifacts/${runId}/${rel}`

export const startRun = (opts: RunOptions) =>
  api.post<{ id: string; status: string }>('/runs', opts).then((r) => r.data)

export const listRuns = (): Promise<RunSummary[]> => {
  if (IS_STATIC_DEPLOYMENT) return Promise.resolve(_demoSummaries())
  return api.get<RunSummary[]>('/runs').then((r) => r.data)
}

export const getRun = (id: string): Promise<Run> => {
  if (IS_STATIC_DEPLOYMENT) return Promise.resolve(_demoRunDetail(id))
  return api.get<Run>(`/runs/${id}`).then((r) => r.data)
}

export const cancelRun = (id: string) =>
  api.delete(`/runs/${id}`).then((r) => r.data)

export const issuesUrl = (id: string) => `${API_BASE}/runs/${id}/issues`
export const reportJsonUrl = (id: string) => `${API_BASE}/runs/${id}/report.json`
export const reportHtmlUrl = (id: string) => `${API_BASE}/runs/${id}/report.html`
export const reportZipUrl = (id: string) => `${API_BASE}/runs/${id}/site-report.zip`

// ------------------------------------------------------------------
// Built-in demo data for static deployments (Vercel without backend)
// ------------------------------------------------------------------
const now = () => Date.now() / 1000

function _demoSummaries(): RunSummary[] {
  const t = now()
  return [
    {
      id: 'demo-shop', url: 'https://shop.example.com/', status: 'completed',
      phase: 'done', pages_done: 2, pages_total: 2,
      issue_counts: { critical: 0, high: 2, medium: 3, low: 1, info: 0 },
      total_issues: 6, overall_score: 70, grade: 'C',
      created_at: t - 3 * 3600, started_at: t - 3 * 3600, finished_at: t - 3 * 3600 + 75,
      duration_s: 75, error: null, is_demo: true,
    },
    {
      id: 'demo-example', url: 'https://example.com/', status: 'completed',
      phase: 'done', pages_done: 1, pages_total: 1,
      issue_counts: { critical: 0, high: 1, medium: 4, low: 3, info: 2 },
      total_issues: 10, overall_score: 60, grade: 'D',
      created_at: t - 26 * 3600, started_at: t - 26 * 3600, finished_at: t - 26 * 3600 + 30,
      duration_s: 30, error: null, is_demo: true,
    },
    {
      id: 'demo-blog', url: 'https://blog.example.org/', status: 'completed',
      phase: 'done', pages_done: 2, pages_total: 2,
      issue_counts: { critical: 0, high: 0, medium: 1, low: 0, info: 3 },
      total_issues: 4, overall_score: 94, grade: 'A',
      created_at: t - 50 * 3600, started_at: t - 50 * 3600, finished_at: t - 50 * 3600 + 45,
      duration_s: 45, error: null, is_demo: true,
    },
    {
      id: 'demo-app', url: 'https://app.example.net/', status: 'cancelled',
      phase: 'cancelled', pages_done: 2, pages_total: 6,
      issue_counts: { critical: 0, high: 1, medium: 2, low: 0, info: 0 },
      total_issues: 3, overall_score: null, grade: null,
      created_at: t - 3 * 86400, started_at: t - 3 * 86400, finished_at: t - 3 * 86400 + 90,
      duration_s: 90, error: null, is_demo: true,
    },
  ]
}

function _demoRunDetail(id: string): Run {
  const summary = _demoSummaries().find((r) => r.id === id)
  if (!summary) throw new Error('Run not found')
  return {
    id: summary.id,
    options: {
      url: summary.url, max_pages: 10, viewports: ['desktop'],
      engines: [], follow_robots: false, delay_ms: 0, timeout_ms: 60000,
    },
    status: summary.status, phase: summary.phase,
    pages_done: summary.pages_done, pages_total: summary.pages_total,
    current_url: null,
    issues: [], pages: [],
    scores: {
      overall: summary.overall_score ?? 0,
      grade: summary.grade ?? '',
      categories: {},
    },
    error: summary.error, is_demo: true,
    created_at: summary.created_at,
    started_at: summary.started_at,
    finished_at: summary.finished_at,
  }
}
